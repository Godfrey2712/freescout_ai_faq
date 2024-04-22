from flask import Flask, render_template, request, jsonify
from bs4 import BeautifulSoup
import openai
import requests
import re
import tempfile
import os

# Initialize Flask app
app = Flask(__name__)

# Define the api key for open-ai here
# Get the API key from the env file
api_key = None
api_key = os.getenv('api_key')   

#Define the api key for freescout here
free_scout_api_key = None
free_scout_api_key = os.getenv('freeScout_api_key')

# Global variable to store the temp file_path
file_path = None

# The default parameters for the open-ai api
openai_parameters = {
    "model": "gpt-4",
    "temperature": 0.3,
    "max_tokens": 2000
}

# Initialize the AI response, customer messages, and support responses
gpt_support_faq = []
support_messages_raw = 0
customer_messages_raw = 0
 
# Define a global variable to track the index of the next message to return
global support_messages_index
support_messages_index = 0
global customer_messages_index
customer_messages_index = 0

# Route to the html
@app.route('/')
def index():
    return render_template('index.html')

# Route to the main function which calls other functions
@app.route('/run_function', methods=['POST'])
def run_function():
    global file_path
    global free_scout_api_key

    # Get the FreeScout API key from the form input
    if free_scout_api_key is None:
        free_scout_api_key = request.form.get('freeScoutApiKey')
    #if free_scout_api_key is None:
        #raise ValueError("FreeScout API key is not set. Please set it in the environment variables or provide it manually.")

    # Get values from frontend for mailbox id and page size
    mailbox_id = request.form.get('mailboxId')
    page_size = int(request.form.get('pageSize'))

    # Extract the flag value from the request
    continue_despite_mismatch = request.form.get('continueDespiteMismatch')
    # Convert to boolean
    continue_despite_mismatch = continue_despite_mismatch == 'true'

    # Freescout udp url with variables
    url = f"https://helpdesk.teamupdraft.com/api/conversations?embed=threads&mailboxId={mailbox_id}&pageSize={page_size}"
    headers = {
        # Freescout API (To generate a new one, speak to system administrator)
        "X-FreeScout-API-Key": free_scout_api_key,
    }

    params = {
        "embed": "threads",
    }
    response = requests.get(url, headers=headers, params=params)

    # Loop for data extractions from freescout
    if response.status_code == 200:
        data = response.json()
        if "_embedded" in data and "conversations" in data["_embedded"]:
            # Initialize counts for message types
            message_counts = {"customer": 0, "message": 0}  
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding="utf-8") as knowledge_file:
                for conversation in data["_embedded"]["conversations"]:
                    if "threadsCount" in conversation and conversation["threadsCount"] > 0:
                        threads = conversation.get("_embedded", {}).get("threads", [])
                        if threads:
                            for thread in threads:
                                customer_messages = []  # To store body values with type customer
                                support_responses = []  # To store body values with type message

                                if thread["type"] == "customer":
                                    customer_messages.append(strip_name_and_email_from_body(thread['body']))
                                elif thread["type"] == "message":
                                    message_counts["message"] += 1
                                    support_responses.append(strip_name_and_email_from_body(thread['body']))

                                # Skip the thread if both customer_messages and support_responses are empty
                                if not customer_messages and not support_responses:
                                    continue

                                # Write customer messages to the file if not empty
                                if customer_messages:
                                    knowledge_file.write("Customer Message: ")
                                    for body in customer_messages:
                                        knowledge_file.write(body + "\n")

                                # Write support responses to the file if not empty
                                if support_responses:
                                    knowledge_file.write("Support Response: ")
                                    for body in support_responses:
                                        knowledge_file.write(body + "\n")

                            knowledge_file.write("=" * 30 + "\n")
                        # Check if the requested number of FAQs matches the actual number of support responses
                requested_faqs = page_size
                actual_responses = message_counts["message"]
                if requested_faqs != actual_responses and not continue_despite_mismatch:
                    return jsonify({'status': 'error', 'message': f'The requested number of FAQs ({requested_faqs}) does not match the actual number of support responses of ({actual_responses}) in the threads'})         
            # Assign file_path to the global variable
            file_path = knowledge_file.name

            summarize_from_file(file_path)

        else:
            print("No conversations found.")
    else:
        print(f"Failed to retrieve conversations. Status code: {response.status_code}")
        print(response.text)

    return "Function executed successfully!"

# Route to get the results
@app.route('/results')
def fetch_results():
    global gpt_support_faq
    global support_messages_raw
    global support_messages_index
    global customer_messages_raw
    global customer_messages_index

    if gpt_support_faq and (support_messages_raw or customer_messages_raw):  
        # Check if there are messages remaining to be returned
        if support_messages_index < len(support_messages_raw):
            # Get the next message from support_messages_raw
            next_support_message = support_messages_raw[support_messages_index]
            next_customer_message = customer_messages_raw[customer_messages_index]
            # Increment the index for the next call
            support_messages_index += 1
            customer_messages_index += 1
            
            # Check if there are messages remaining in gpt_support_faq
            if gpt_support_faq:
                next_gpt_message = gpt_support_faq[0]  # Get the next message
                gpt_support_faq = gpt_support_faq[1:]  # Remove the first message from the list
            else:
                next_gpt_message = "No more AI-generated messages available."

            # Manage the response from the request
            response_data = {
                "status": "success",
                "messages": next_gpt_message + "<br><br>",
                "original_messages": "<b>ORIGINAL MESSAGE:</b><br><br>" + next_customer_message + "<br> <br>" + "<b>ORIGINAL RESPONSE:</b><br><br>" + next_support_message + "\n" "<br> <br>" + "=" * 60 + "<br> <br>"
            }
            return jsonify(response_data)
        else:
            return jsonify({"status": "success", "message": "No more support messages available."})
    else:
        return jsonify({"status": "error", "message": "No support messages found."})

# Clean data 1
def extract_text_from_html(html):
    if html is not None:
        soup = BeautifulSoup(html, 'html.parser')
        return soup.get_text()
    return ""

# Clean data 2
def strip_name_and_email_from_body(body):
    if body is not None:
        # Define regular expressions to match name, email, URL, and address patterns
        name_pattern = re.compile(r"Your Name:(.*?)(\n|$)")
        email_pattern = re.compile(r"Email:(.*?)(\n|$)")
        email_pattern_2 = re.compile(r"email address:(.*?)(\n|$)")
        email_pattern_3 = re.compile(r"E-mail:(.*?)(\n|$)")
        url_pattern = re.compile(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+")
        address_pattern = re.compile(r"\b\d{1,5}\s+[\w\s]+(?:\s+\w+){1,2}\b")

        # Replace matched patterns with an empty string
        body_without_name = name_pattern.sub('', body)
        body_without_email = email_pattern.sub('', body_without_name)
        body_without_email_2 = email_pattern_2.sub('', body_without_email)
        body_without_email_3 = email_pattern_3.sub('', body_without_email_2)
        body_without_url = url_pattern.sub('', body_without_email_3)
        body_without_address = address_pattern.sub('', body_without_url)

        # Extract text from HTML
        cleaned_body = extract_text_from_html(body_without_address)
        # Remove words containing "@" (emails)
        cleaned_body = ' '.join([word for word in cleaned_body.split() if '@' not in word])
        # Remove words containing "+" (emails)
        cleaned_body = ' '.join([word for word in cleaned_body.split() if '+' not in word])

        return cleaned_body

    return ""

# AI prompt for generating the FAQ from freescout
def summarize(text, is_customer_message=True):
    global api_key
    # If API key is not provided from the environment variable
    if api_key is None:  
        # Get the API key from environment variables
        api_key = request.form.get('apiKey')
    # If API key is not found in both frontend input and environment variables
    #if api_key is None:  
        #raise ValueError("OpenAI API key is not set. Please set it in the environment variables or provide it manually.")
    openai.api_key = api_key

    if is_customer_message:
        instruction = f"If it is a customer message, summarize it into an FAQ topic while retaining context: {text}"
        role = "user"
    else:
        instruction = f"""
        From {text}, generate one meaningful FAQ topic and one answer to the FAQ.
        Seperate them with one line.
        """
        role = "assistant"

    # Paramaterizing the open-ai variables
    prompt = {"role": role, "content": instruction}
    response = openai.ChatCompletion.create(
        model=openai_parameters["model"],
        messages=[prompt],
        temperature=openai_parameters["temperature"],
        max_tokens=openai_parameters["max_tokens"]
    )
    return response.choices[0].message['content'].strip().replace('\"', '')

# Parse the freescout data to the model for inference
def summarize_from_file(file_path):
    with open(file_path, 'r') as file:
        # Split the content by threads, excluding the first and last split parts which are not actual threads
        content = file.read()
        threads = content.split("=" * 30 + "\n")[1:-1]

    # Initialize lists to hold the concatenated customer requests and support messages
    customer_requests = []
    support_messages = []

    for thread in threads:
        # Initialize variables to hold concatenated messages for the current thread
        customer_message = ""
        support_response = ""

        # Process each line in the thread
        thread_lines = thread.strip().split('\n')
        for line in thread_lines:
            if ": " not in line:
                continue  # Skip lines that don't contain the key-value separator

            key, value = line.split(": ", 1)
            value = value.strip()

            # Concatenate messages based on their type
            if key == "Customer Message":
                # Concatenate with a newline if customer_message is not empty
                customer_message += ("\n" "<br>" if customer_message else "") + value
            elif key == "Support Response":
                # Similarly, concatenate with a newline for support_response
                support_response += ("\n" "<br>" if support_response else "") + value

        # After processing each thread, append the concatenated messages to their respective lists
        if customer_message:
            customer_requests.append(customer_message)
        if support_response:
            support_messages.append(support_response)

    # The data file will be used as the chatbot knowledge file
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding="utf-8") as temp_categorized_file:
        global gpt_support_faq
        for i, (customer_request, support_message) in enumerate(zip(customer_requests, support_messages)):
            # Skip summarizing the customer request
            # Summarize support message only
            summarized_support_message = summarize(support_message, is_customer_message=False)

            # Write to temp file
            temp_categorized_file.write(f"{i+1}. {summarized_support_message}\n")
            temp_categorized_file.write("=" * 100 + "\n")

            # Storing the last summarized message globally if needed
            # Append new summary to the global list
            gpt_support_faq.append(f"{i+1}. {summarized_support_message}")
            print (gpt_support_faq)

            global support_messages_raw
            support_messages_raw = []  # Initialize as an empty list
            for i, message in enumerate(support_messages, start=1):
                support_messages_raw.append(f"{i}. {message}")  # Append each message along with its index

            global customer_messages_raw
            customer_messages_raw = []  # Initialize as an empty list
            for i, message in enumerate(customer_requests, start=1):
                customer_messages_raw.append(f"{i}. {message}")  # Append each message along with its index
            
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
