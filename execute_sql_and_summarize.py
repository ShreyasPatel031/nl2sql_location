import json
import time
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting
from google.api_core.exceptions import ResourceExhausted


def call_gemini_api(prompt):
    # Initialize Vertex AI with your project and location
    vertexai.init(project="ai-demos-439118", location="us-central1")

    # Load the Gemini Pro model
    model = GenerativeModel(
        model_name="gemini-1.5-pro-002",
    )

    # Configuration for generation
    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 0.2,
        "top_p": 0.95,
    }


    max_retries = 10
    backoff_factor = 2
    for retry in range(max_retries):
        try:
            # Generate content using the model
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=False,
            )
            response_text = response.text.strip()
            return response_text
        except ResourceExhausted as e:
            if retry < max_retries - 1:
                sleep_time = backoff_factor ** retry
                time.sleep(sleep_time)
                continue
            else:
                raise e
        except Exception as e:
            raise e

def execute_sql_query(sql_query):
    client = bigquery.Client()
    query_job = client.query(sql_query)
    results = query_job.result()
    return results

def summarize_results(sql_query, rows):
    # Convert results to JSON
    results_json = json.dumps(rows, default=str)

    # Create a prompt to summarize the results
    summary_prompt = f"""
SQL Query:
{sql_query}

Results:
{results_json}

Please provide a concise summary of the query results, highlighting key findings.
"""
    # Call Gemini Pro API to generate the summary
    summary = call_gemini_api(summary_prompt)

    # Clean up the summary text
    summary = clean_summary_text(summary)

    return summary

def clean_summary_text(text):
    # Remove any extraneous whitespace characters
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = ' '.join(text.split())

    # Handle any special characters or encoding issues
    text = text.encode('ascii', 'ignore').decode('ascii')

    return text
