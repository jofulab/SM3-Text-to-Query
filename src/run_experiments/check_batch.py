"""Print the status of an OpenAI batch job: python check_batch.py <batch_id>"""
import sys

from openai import OpenAI

if len(sys.argv) < 2:
    print("Please provide the batch ID as a command-line argument.")
    sys.exit(1)

batch = OpenAI().batches.retrieve(sys.argv[1])
print(f"status: {batch.status}")
print(f"output_file_id: {batch.output_file_id}")
print(f"request_counts: {batch.request_counts}")
