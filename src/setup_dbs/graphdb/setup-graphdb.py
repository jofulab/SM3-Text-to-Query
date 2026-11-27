"""
Create the SM3 GraphDB repository and load the Synthea RDF data into it.

By default the TTL files shipped in data/synthea_ttl.zip are imported; these are the exact files used for the
paper. Set GRAPHDB_CONVERT_FROM_CSV=1 to instead convert the Synthea CSVs in SYNTHEA_DATA with the bundled
synthea-rdf converter (useful for custom Synthea data).

Settings come from config_graphdb.yml and can be overridden with the env vars GRAPHDB_URL, GRAPHDB_REPOSITORY,
GRAPHDB_USERNAME, GRAPHDB_PASSWORD, TTL_ZIP and SYNTHEA_DATA.
"""
import logging
import os
import subprocess
import sys
import tempfile
import time
import zipfile

import requests
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HERE = os.path.dirname(os.path.abspath(__file__))
CONVERTER_DIR = os.path.join(HERE, 'synthea-rdf-converter-fork')

TEST_QUERY = """
PREFIX syn: <https://knacc.umbc.edu/dae-young/kim/ontologies/synthea#>
PREFIX pl: <http://www.w3.org/1999/02/22-rdf-syntax-ns#PlainLiteral>
SELECT DISTINCT ?first ?last
WHERE {
  ?organization a syn:Organization; syn:id ?organizationId; syn:name 'ROYAL OF FAIRHAVEN NURSING CENTER'^^pl: .
  ?encounter a syn:Encounter; syn:organizationId ?organizationId; syn:patientId ?patientId .
  ?patient a syn:Patient; syn:id ?patientId; syn:first ?first; syn:last ?last .
}
"""
EXPECTED = [('Glendora96', 'Tillman293')]


def load_config():
    with open(os.getenv('GRAPHDB_CONFIG', os.path.join(HERE, 'config_graphdb.yml'))) as f:
        config = yaml.safe_load(f)
    return {
        'server_uri': os.getenv('GRAPHDB_URL', config.get('server_uri', 'http://sm3-graphdb:7200')).rstrip('/'),
        'repository': os.getenv('GRAPHDB_REPOSITORY', config.get('repository', 'sm3_graphdb')),
        'username': os.getenv('GRAPHDB_USERNAME', config.get('username', 'admin')),
        'password': os.getenv('GRAPHDB_PASSWORD', config.get('password', 'root')),
        'ttl_zip': os.getenv('TTL_ZIP', config.get('ttl_zip', '/app/data/synthea_ttl.zip')),
        'synthea_data': os.getenv('SYNTHEA_DATA', config.get('synthea_data', '/app/data/synthea_data')),
    }


class GraphDB:
    def __init__(self, cfg):
        self.base = cfg['server_uri']
        self.repository = cfg['repository']
        self.auth = (cfg['username'], cfg['password'])

    def wait(self, max_retries=60, delay_seconds=5):
        for attempt in range(max_retries):
            try:
                if requests.get(f"{self.base}/rest/repositories", auth=self.auth, timeout=10).ok:
                    logger.info(f"GraphDB is up at {self.base}")
                    return True
            except requests.RequestException as e:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: GraphDB not reachable yet ({e})")
            time.sleep(delay_seconds)
        return False

    def repository_exists(self):
        repos = requests.get(f"{self.base}/rest/repositories", auth=self.auth, timeout=30)
        repos.raise_for_status()
        return any(r.get('id') == self.repository for r in repos.json())

    def statement_count(self):
        r = requests.get(f"{self.base}/repositories/{self.repository}/size", auth=self.auth, timeout=60)
        r.raise_for_status()
        return int(r.text)

    def create_repository(self):
        with open(os.path.join(HERE, 'repo-config.ttl')) as f:
            # repo-config.ttl names the repository "sm3_graphdb"; follow GRAPHDB_REPOSITORY if it was overridden
            repo_config = f.read().replace('"sm3_graphdb"', f'"{self.repository}"')
        r = requests.post(f"{self.base}/rest/repositories", auth=self.auth, timeout=120,
                          files={'config': ('repo-config.ttl', repo_config, 'text/turtle')})
        if not r.ok:
            raise RuntimeError(f"Creating repository {self.repository} failed: HTTP {r.status_code} {r.text}")
        logger.info(f"Created repository {self.repository}")

    def import_ttl_files(self, ttl_dir):
        files = sorted(os.path.join(root, f) for root, _, names in os.walk(ttl_dir) for f in names if f.endswith('.ttl'))
        if not files:
            raise RuntimeError(f"No .ttl files found in {ttl_dir}")
        for path in files:
            start = time.time()
            with open(path, 'rb') as f:
                r = requests.post(f"{self.base}/repositories/{self.repository}/statements", data=f, auth=self.auth,
                                  headers={'Content-Type': 'text/turtle'})
            if r.status_code != 204:
                raise RuntimeError(f"Importing {os.path.basename(path)} failed: HTTP {r.status_code} {r.text[:500]}")
            logger.info(f"Imported {os.path.basename(path)} in {time.time() - start:.0f}s")

    def run_test_query(self):
        r = requests.post(f"{self.base}/repositories/{self.repository}", data={'query': TEST_QUERY}, auth=self.auth,
                          headers={'Accept': 'application/sparql-results+json'}, timeout=300)
        if not r.ok:
            logger.error(f"Test query failed: HTTP {r.status_code} {r.text[:500]}")
            return False
        rows = [(b['first']['value'], b['last']['value']) for b in r.json()['results']['bindings']]
        print(f"Test query result: {rows}")
        if rows == EXPECTED:
            print("✅ Test passed: Found expected patient Glendora96 Tillman293")
            return True
        print(f"❌ Test failed, expected {EXPECTED}")
        return False


def prepare_ttl_dir(cfg, workdir):
    """Return a folder with the TTL files to import."""
    if os.getenv('GRAPHDB_CONVERT_FROM_CSV', '0') == '1':
        logger.info(f"Converting the Synthea CSVs in {cfg['synthea_data']} to RDF (this takes a while) ...")
        env = dict(os.environ, SYNTHEA_DATA=cfg['synthea_data'])
        subprocess.run([sys.executable, os.path.join(CONVERTER_DIR, 'conversion.py')], check=True, env=env)
        return os.path.join(CONVERTER_DIR, 'temporary_ttl_files')
    logger.info(f"Extracting {cfg['ttl_zip']} ...")
    with zipfile.ZipFile(cfg['ttl_zip']) as zf:
        zf.extractall(workdir)
    return workdir


def main():
    cfg = load_config()
    db = GraphDB(cfg)
    if not db.wait():
        logger.error(f"GraphDB at {db.base} did not become reachable")
        raise SystemExit(1)

    if db.repository_exists() and db.statement_count() > 0:
        print(f"Repository {db.repository} already contains data. Import skipped.")
    else:
        if not db.repository_exists():
            db.create_repository()
        with tempfile.TemporaryDirectory() as workdir:
            db.import_ttl_files(prepare_ttl_dir(cfg, workdir))
        print(f"Data has been imported into GraphDB repository {db.repository} ({db.statement_count()} statements)")

    raise SystemExit(0 if db.run_test_query() else 1)


if __name__ == "__main__":
    main()
