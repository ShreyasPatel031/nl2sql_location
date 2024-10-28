import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting
import re
import time
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

def generate_sql_query(user_prompt, business_context, schema_information, prompt_query_pairs):
    # Construct the prompt for Gemini Pro
    full_prompt = f"""
User Prompt:
{user_prompt}

Business Context:
{business_context}

Schema Information:
{schema_information}

Example Prompt and SQL Query Pairs:
{prompt_query_pairs}

Instructions:
- Generate an SQL query based on the user prompt and the information provided.
- Only provide the SQL query without any explanations, comments, or markdown formatting.
- Ensure the SQL query is syntactically correct and aligns with the provided schema.

SQL Query:
"""
    # Call Gemini Pro API
    raw_sql_query = call_gemini_api(full_prompt)
    
    # Format the SQL query to remove unnecessary parts
    formatted_sql_query = format_sql_query(raw_sql_query)
    
    return formatted_sql_query

def format_sql_query(raw_sql_query):
    # Remove markdown code blocks
    sql_query = raw_sql_query.replace("```sql", "").replace("```", "").strip()
    
    # Remove any SQL comments
    sql_query = re.sub(r"--.*\n", "", sql_query)  # Remove single-line comments
    sql_query = re.sub(r"/\*[\s\S]*?\*/", "", sql_query)  # Remove multi-line comments
    
    # Remove any text after a semicolon
    sql_query = sql_query.split(';')[0] + ';'
    
    # Remove any extra whitespace
    sql_query = ' '.join(sql_query.split())
    
    return sql_query
