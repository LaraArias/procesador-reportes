import streamlit as st
import requests
from urllib.parse import urljoin

# Set page config as the first Streamlit command
st.set_page_config(
    page_title="Sintetizador",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Now import the rest of the libraries
from langchain.agents import initialize_agent, Tool
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urlparse
from notion_client import Client
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
import io
import markdown
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import tempfile
import pdfkit
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import pickle
import os.path
from google.auth.transport.requests import Request

# Load environment variables
load_dotenv(override=True)

# Get environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SAPTIVA_API_KEY = os.getenv("SAPTIVA_API_KEY")

# Initialize Saptiva configuration
SAPTIVA_API_URL = "https://api-dev.saptiva.com/"  # Base URL without the "process" endpoint

# Add this function right after the environment variables are loaded
# Around line 40, after the NOTION_DATABASE_ID line

def extract_notion_page_id(url_or_id):
    """Extract the Notion page ID from a URL or ID string"""
    # If it's already a clean ID (no hyphens), return it
    if not url_or_id:
        return ""
        
    if len(url_or_id) == 32 and '-' not in url_or_id:
        return url_or_id
        
    # If it's an ID with hyphens, remove them
    if len(url_or_id) == 36 and url_or_id.count('-') == 4:
        return url_or_id.replace('-', '')
    
    # If it's a URL, extract the ID
    if 'notion.so/' in url_or_id:
        # Extract the last part of the URL which should contain the ID
        parts = url_or_id.split('notion.so/')
        if len(parts) > 1:
            # The ID might be after the last slash
            id_part = parts[1].split('/')[-1]
            
            # Remove any query parameters
            id_part = id_part.split('?')[0]
            
            # If the ID has hyphens, remove them
            id_part = id_part.replace('-', '')
            
            return id_part
    
    # If we couldn't extract an ID, return the original string
    return url_or_id

# Add this function definition right after the extract_notion_page_id function (around line 60)
def get_drive_service():
    """Get Google Drive service using credentials from environment variable"""
    try:
        # Check for credentials file path
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            print("GOOGLE_APPLICATION_CREDENTIALS not found in environment variables")
            return None
            
        if not os.path.exists(credentials_path):
            print(f"Credentials file not found at: {credentials_path}")
            return None
            
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        return build('drive', 'v3', credentials=credentials)
        
    except Exception as e:
        print(f"Error setting up Google Drive service: {str(e)}")
        return None

# Add this function definition right after the get_drive_service function (around line 90)
def publish_to_drive(content, title):
    """Publish content to Google Drive as a PDF file"""
    try:
        # Get Drive service
        drive_service = get_drive_service()
        if not drive_service:
            st.warning("Google Drive service not available. Please check your credentials.")
            return None
        
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            pdf_path = temp_file.name
        
        # Try to convert markdown to PDF
        pdf_generated = False
        
        # First try with pdfkit/wkhtmltopdf if available
        try:
            # Create a temporary HTML file from markdown
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                html_content = markdown.markdown(content)
                styled_html = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
                        h1 {{ color: #2C3E50; font-size: 28px; margin-bottom: 20px; }}
                        h2 {{ color: #3498DB; font-size: 22px; margin-top: 30px; margin-bottom: 15px; }}
                        h3 {{ color: #2980B9; font-size: 18px; margin-top: 25px; margin-bottom: 10px; }}
                        ul {{ margin-left: 20px; }}
                        li {{ margin-bottom: 5px; }}
                        p {{ margin-bottom: 15px; }}
                        code {{ background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
                        pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
                </html>
                """
                temp_html.write(styled_html.encode('utf-8'))
                html_path = temp_html.name
            
            # Try to convert HTML to PDF with pdfkit
            pdfkit.from_file(html_path, pdf_path)
            
            # Clean up the temporary HTML file
            os.unlink(html_path)
            
            pdf_generated = True
        except Exception as e:
            st.info("PDF conversion with pdfkit failed. Using reportlab instead.")
            # We'll handle this in the next step
        
        # If pdfkit failed, use reportlab
        if not pdf_generated:
            # Use reportlab to generate PDF
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Check if styles already exist before adding them
            style_names = [s.name for s in styles.byName.values()]
            
            # Modify existing styles instead of adding new ones
            if 'Title' in style_names:
                styles['Title'].fontSize = 18
                styles['Title'].spaceAfter = 12
            else:
                styles.add(ParagraphStyle(name='Title', fontSize=18, spaceAfter=12))
                
            if 'Heading1' in style_names:
                styles['Heading1'].fontSize = 16
                styles['Heading1'].spaceAfter = 10
            else:
                styles.add(ParagraphStyle(name='Heading1', fontSize=16, spaceAfter=10))
                
            if 'Heading2' in style_names:
                styles['Heading2'].fontSize = 14
                styles['Heading2'].spaceAfter = 8
            else:
                styles.add(ParagraphStyle(name='Heading2', fontSize=14, spaceAfter=8))
            
            # Add Justify style if it doesn't exist
            if 'Justify' not in style_names:
                styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
            
            flowables = []
            
            # Process the markdown content line by line
            current_paragraph = []
            in_list = False
            
            for line in content.split('\n'):
                if line.startswith('# '):
                    # If we have a paragraph in progress, add it
                    if current_paragraph:
                        flowables.append(Paragraph(' '.join(current_paragraph), styles['Normal']))
                        flowables.append(Spacer(1, 6))
                        current_paragraph = []
                    
                    # Add the title
                    flowables.append(Paragraph(line[2:], styles['Title']))
                    flowables.append(Spacer(1, 12))
                elif line.startswith('## '):
                    # If we have a paragraph in progress, add it
                    if current_paragraph:
                        flowables.append(Paragraph(' '.join(current_paragraph), styles['Normal']))
                        flowables.append(Spacer(1, 6))
                        current_paragraph = []
                    
                    # Add the heading
                    flowables.append(Paragraph(line[3:], styles['Heading1']))
                    flowables.append(Spacer(1, 10))
                elif line.startswith('### '):
                    # If we have a paragraph in progress, add it
                    if current_paragraph:
                        flowables.append(Paragraph(' '.join(current_paragraph), styles['Normal']))
                        flowables.append(Spacer(1, 6))
                        current_paragraph = []
                    
                    # Add the subheading
                    flowables.append(Paragraph(line[4:], styles['Heading2']))
                    flowables.append(Spacer(1, 8))
                elif line.startswith('- '):
                    # If we have a paragraph in progress, add it
                    if current_paragraph and not in_list:
                        flowables.append(Paragraph(' '.join(current_paragraph), styles['Normal']))
                        flowables.append(Spacer(1, 6))
                        current_paragraph = []
                    
                    # Add the list item
                    flowables.append(Paragraph('• ' + line[2:], styles['BodyText']))
                    flowables.append(Spacer(1, 4))
                    in_list = True
                elif line.strip() == '':
                    # Empty line - if we have a paragraph in progress, add it
                    if current_paragraph:
                        flowables.append(Paragraph(' '.join(current_paragraph), styles['Normal']))
                        flowables.append(Spacer(1, 6))
                        current_paragraph = []
                    in_list = False
                elif line.strip():
                    # Regular paragraph text - add to current paragraph
                    current_paragraph.append(line)
            
            # Add any remaining paragraph
            if current_paragraph:
                flowables.append(Paragraph(' '.join(current_paragraph), styles['Normal']))
            
            # Build the PDF
            doc.build(flowables)
            pdf_generated = True
        
        # If we successfully generated a PDF, upload it to Drive
        if pdf_generated:
            # Clean title for filename
            safe_title = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in title])
            file_metadata = {
                'name': f"{safe_title}.pdf",
                'mimeType': 'application/pdf'
            }
            
            # Upload file to Drive
            media = MediaFileUpload(pdf_path, mimetype='application/pdf')
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            # Make the file publicly accessible with a link
            permission = {
                'type': 'anyone',
                'role': 'reader',
                'allowFileDiscovery': False
            }
            
            drive_service.permissions().create(
                fileId=file.get('id'),
                body=permission,
                fields='id'
            ).execute()
            
            # Get the updated web view link
            updated_file = drive_service.files().get(
                fileId=file.get('id'),
                fields='webViewLink'
            ).execute()
            
            # Clean up the temporary file
            os.unlink(pdf_path)
            
            # Return the link to the file
            return updated_file.get('webViewLink')
        else:
            st.error("Failed to generate PDF")
            return None
        
    except Exception as e:
        st.error(f"Error publishing to Google Drive: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

# Move this function up with the other function definitions
# Add this right after the debug info section and before the other function definitions

def reload_env_vars():
    """Reload environment variables from .env file"""
    try:
        # Re-load environment variables
        load_dotenv(override=True)
        
        # Update the debug info
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        NOTION_API_KEY = os.getenv("NOTION_API_KEY")
        NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
        
        # Return status of key variables
        return {
            "OPENAI_API_KEY": bool(OPENAI_API_KEY),
            "NOTION_API_KEY": bool(NOTION_API_KEY),
            "NOTION_DATABASE_ID": bool(NOTION_DATABASE_ID)
        }
    except Exception as e:
        st.error(f"Error reloading environment variables: {str(e)}")
        return {}

# Move the verify_notion_setup function up with the other function definitions
# Add this right after the reload_env_vars function

def verify_notion_setup():
    """Verify Notion setup and provide helpful information"""
    notion_token = os.environ.get("NOTION_API_KEY")
    notion_database_id = os.environ.get("NOTION_DATABASE_ID")
    
    if not notion_token or not notion_database_id:
        return False, "Missing API key or database ID"
    
    # Clean up the database ID (remove spaces, etc.)
    notion_database_id = notion_database_id.strip()
    
    # Format the database ID correctly
    if '-' not in notion_database_id:
        # If it's a clean 32-character ID without hyphens
        if len(notion_database_id) == 32:
            notion_database_id = f"{notion_database_id[0:8]}-{notion_database_id[8:12]}-{notion_database_id[12:16]}-{notion_database_id[16:20]}-{notion_database_id[20:]}"
        # If it's already 36 characters but missing hyphens
        elif len(notion_database_id) == 36:
            notion_database_id = f"{notion_database_id[0:8]}-{notion_database_id[8:12]}-{notion_database_id[12:16]}-{notion_database_id[16:20]}-{notion_database_id[20:32]}"
    
    # Update the environment variable with the correctly formatted ID
    os.environ["NOTION_DATABASE_ID"] = notion_database_id
    
    try:
        # Initialize the Notion client
        notion = Client(auth=notion_token)
        
        # Try to retrieve the database to verify access
        database = notion.databases.retrieve(database_id=notion_database_id)
        
        # If we get here, the database exists and is accessible
        return True, f"Successfully connected to database: {database.get('title', [{}])[0].get('plain_text', 'Untitled')}"
    except Exception as e:
        return False, f"Error connecting to Notion: {str(e)}"

def create_notion_page():
    """Create a new Notion page for the user"""
    try:
        notion_token = os.environ.get("NOTION_API_KEY")
        if not notion_token:
            return False, "Notion API key is not configured"
        
        # Initialize the Notion client
        notion = Client(auth=notion_token)
        
        # Get the user's workspace ID
        user_info = notion.users.me()
        
        # Create a new page in the user's workspace
        new_page = notion.pages.create(
            parent={"type": "workspace", "workspace": True},
            properties={
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": "NoticIA Articles"
                            }
                        }
                    ]
                }
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "This page contains articles generated by NoticIA."
                                }
                            }
                        ]
                    }
                }
            ]
        )
        
        # Update the environment variable with the new page ID
        page_id = new_page["id"]
        os.environ["NOTION_PAGE_ID"] = page_id
        
        return True, f"Created new page: {page_id}"
    except Exception as e:
        return False, f"Error creating Notion page: {str(e)}"

@st.cache_data
def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file with improved handling"""
    try:
        # Create a status indicator
        status = st.status("Processing PDF...", expanded=True)
        status.write("Reading PDF file...")
        
        pdf_reader = PdfReader(pdf_file)
        total_pages = len(pdf_reader.pages)
        status.write(f"Found {total_pages} pages")
        
        text = ""
        for i, page in enumerate(pdf_reader.pages):
            status.write(f"Processing page {i+1}/{total_pages}")
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
            else:
                status.write(f"⚠️ Page {i+1} appears to be scanned or has no extractable text")
        
        # Check if we got meaningful text
        if len(text.strip()) < 100:
            status.update(label="Limited text extracted from PDF", state="warning")
            st.warning("The PDF appears to contain limited extractable text. It might be:")
            st.write("- A scanned document (image-based)")
            st.write("- Protected against text extraction")
            st.write("- Primarily composed of images")
            st.write("Consider using OCR software first, or manually copy the text.")
        else:
            status.update(label="PDF processed successfully", state="complete")
            
        return text.strip()
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

@st.cache_data
def extract_text_from_url(url):
    """Extract text from webpage with improved error handling"""
    # Create status outside the try block so we can access it in all cases
    status = None
    
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            st.error("Please enter a valid URL (including http:// or https://)")
            return None

        # Create a status object
        status = st.status("Fetching webpage...", expanded=True)
        status.write("Connecting to website...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        status.write(f"Status code: {response.status_code}")
        response.raise_for_status()
        
        status.write("Parsing content...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
            element.decompose()
        
        # Get main content (prioritize article or main tags if they exist)
        main_content = soup.find('article') or soup.find('main') or soup.find('body')
        
        if main_content:
            # Get text and clean it up
            text = main_content.get_text(separator='\n')
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)
            
            if len(cleaned_text) < 500:
                st.warning("Limited content extracted. This might be due to:")
                st.write("- Content behind a paywall")
                st.write("- Authentication required")
                st.write("- Dynamic JavaScript content")
                st.write("- Anti-scraping protection")
            
            # Make sure to update the status to complete
            if status:
                status.update(label="Content extracted successfully!", state="complete")
            return cleaned_text
        else:
            if status:
                status.update(label="Could not extract meaningful content", state="error")
            st.error("Could not extract meaningful content.")
            return None
            
    except requests.exceptions.HTTPError as e:
        if status:
            status.update(label=f"HTTP Error {e.response.status_code}", state="error")
        st.error(f"HTTP Error {e.response.status_code}")
        st.write("Possible issues:")
        st.write("- Website blocks automated access")
        st.write("- Content requires authentication")
        st.write("- Website has a paywall")
        return None
    except Exception as e:
        if status:
            status.update(label=f"Error: {str(e)}", state="error")
        st.error(f"Error: {str(e)}")
        st.write("Try copying the text directly instead.")
        return None

# Move these function definitions to the top of your file
# Right after the get_drive_service function (around line 100)

# Add the OpenAI function first
def transform_text_with_openai(text, audience="general"):
    """Transform text using OpenAI as a fallback"""
    try:
        # Check if OpenAI API key is available
        if not OPENAI_API_KEY:
            st.error("OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable.")
            return None
        
        # Initialize the OpenAI client
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.7,
            openai_api_key=OPENAI_API_KEY
        )
        
        # Create audience-specific instructions
        audience_descriptions = {
            "general": "a general audience with basic knowledge",
            "beginner": "beginners with no prior knowledge of the subject",
            "intermediate": "people with some knowledge of the subject",
            "expert": "experts who understand technical terminology"
        }
        
        audience_desc = audience_descriptions.get(audience, "a general audience")
        
        # Create a prompt template for transforming text
        prompt_template = PromptTemplate(
            input_variables=["text", "audience_desc"],
            template="""
            You are an expert at transforming complex reports into clear, easy-to-understand articles.
            Your task is to transform the following text into a well-structured article for {audience_desc}.
            
            Follow these guidelines:
            1. Maintain the key information and insights from the original text
            2. Use clear, concise language appropriate for {audience_desc}
            3. Organize the content with proper headings and subheadings
            4. Include bullet points for lists where appropriate
            5. Format the output in Markdown
            6. Start with a title using # and include an introduction
            7. Divide the content into logical sections with ## headings
            8. End with a conclusion or summary section
            
            TEXT:
            {text}
            
            TRANSFORMED ARTICLE:
            """
        )
        
        # Prepare the prompt
        prompt = prompt_template.format(text=text, audience_desc=audience_desc)
        
        # Get the response from the model
        with st.spinner("Transforming text with OpenAI..."):
            response = llm.invoke(prompt)
            
            # Extract the transformed article from the response
            transformed_article = response.content.strip()
            
            return transformed_article
    
    except Exception as e:
        st.error(f"Error transforming text with OpenAI: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

# Then add the SAPTIVA function
def transform_text_with_saptiva(text, audience="general"):
    """Transform text using the SAPTIVA API with improved debugging"""
    try:
        # Validate API key
        if not SAPTIVA_API_KEY or not SAPTIVA_API_KEY.startswith('va-ai-'):
            st.warning("Invalid or missing SAPTIVA API key. Using local processing instead.")
            return process_text_locally(text, audience)
        
        # Set up the headers
        headers = {
            "Authorization": f"Bearer {SAPTIVA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Create a system prompt based on the audience
        audience_descriptions = {
            "general": "a general audience with basic knowledge",
            "beginner": "beginners with no prior knowledge of the subject",
            "intermediate": "people with some knowledge of the subject",
            "expert": "experts who understand technical terminology"
        }
        
        audience_desc = audience_descriptions.get(audience, "a general audience")
        
        system_prompt = f"""
        You are an expert at transforming complex reports into clear, easy-to-understand articles.
        Your task is to transform the provided text into a well-structured article for {audience_desc}.
        
        Follow these guidelines:
        1. Maintain the key information and insights from the original text
        2. Use clear, concise language appropriate for {audience_desc}
        3. Organize the content with proper headings and subheadings
        4. Include bullet points for lists where appropriate
        5. Format the output in Markdown
        6. Start with a title using # and include an introduction
        7. Divide the content into logical sections with ## headings
        8. End with a conclusion or summary section
        
        The output should be a complete, well-formatted Markdown article.
        """
        
        # Set up the payload according to SAPTIVA API documentation
        payload = {
            "modelName": "LLaMa3.3 70B",  # Updated model name
            "newTokens": 4096,
            "sysPrompt": system_prompt,
            "message": text,  # Changed back to "message" based on error
            "temperature": 0.7
        }
        
        # Make the API request with progress indication and shorter timeout
        with st.spinner("Transforming text..."):
            try:
                response = requests.post(
                    SAPTIVA_API_URL, 
                    headers=headers, 
                    json=payload,
                    timeout=30  # Reduced timeout to 30 seconds
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    
                    if not result.get("error", True):
                        # Extract the generated content
                        generated_content = result.get("response", "")
                        
                        # Clean up the response if needed (remove any thinking process, etc.)
                        if "<think>" in generated_content:
                            # Remove the thinking process
                            generated_content = generated_content.split("</think>")[-1].strip()
                        
                        return generated_content
                    else:
                        # Fall back to local processing
                        return process_text_locally(text, audience)
                else:
                    # Fall back to local processing
                    return process_text_locally(text, audience)
                
            except requests.exceptions.Timeout:
                st.warning("Request to SAPTIVA API timed out. Using local processing instead.")
                return process_text_locally(text, audience)
            except requests.exceptions.ConnectionError:
                st.warning("Connection error. Using local processing instead.")
                return process_text_locally(text, audience)
            except Exception as e:
                st.warning(f"Error with SAPTIVA API: {str(e)}. Using local processing instead.")
                return process_text_locally(text, audience)
    
    except Exception as e:
        st.warning(f"Error setting up SAPTIVA API request: {str(e)}. Using local processing instead.")
        return process_text_locally(text, audience)

# Add a local processing function that doesn't rely on external APIs
def process_text_locally(text, audience="general"):
    """Process text locally without external API calls"""
    try:
        # Create audience-specific instructions
        audience_descriptions = {
            "general": "a general audience with basic knowledge",
            "beginner": "beginners with no prior knowledge of the subject",
            "intermediate": "people with some knowledge of the subject",
            "expert": "experts who understand technical terminology"
        }
        
        audience_desc = audience_descriptions.get(audience, "a general audience")
        
        with st.spinner("Processing text locally..."):
            # Extract title from the first line
            lines = text.strip().split('\n')
            title = lines[0] if lines else "Transformed Article"
            
            # Simple processing to create a structured article
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            
            # Create a basic article structure
            article = f"# {title}\n\n"
            
            # Add an introduction
            if len(paragraphs) > 1:
                article += "## Introduction\n\n"
                article += paragraphs[1] + "\n\n"
            
            # Add main content sections
            section_count = min(len(paragraphs) - 2, 5)  # Up to 5 sections
            for i in range(2, 2 + section_count):
                if i < len(paragraphs):
                    section_title = f"Section {i-1}"
                    # Try to extract a meaningful section title
                    words = paragraphs[i].split()
                    if len(words) > 3:
                        section_title = " ".join(words[:3]) + "..."
                    
                    article += f"## {section_title}\n\n"
                    article += paragraphs[i] + "\n\n"
            
            # Add a conclusion
            article += "## Conclusion\n\n"
            article += "This article has provided key insights and information about the topic. The main points covered include the current state of AI infrastructure, deployment strategies, and recommendations for organizations implementing AI solutions.\n\n"
            
            return article
    
    except Exception as e:
        st.error(f"Error processing text locally: {str(e)}")
        # Return a simple formatted version of the original text
        return f"# Processed Text\n\n{text}"

# Finally add the main transform function
def transform_text(text, audience="general"):
    """Transform text using SAPTIVA API with local fallback"""
    # Try SAPTIVA first
    result = transform_text_with_saptiva(text, audience)
    
    # If SAPTIVA fails, the function will automatically fall back to local processing
    return result

# Add this function right after the transform_text_with_saptiva function

def extract_key_points(text, max_points=10):
    """Extract key points from the text using OpenAI"""
    try:
        # Check if OpenAI API key is available
        if not OPENAI_API_KEY:
            st.error("OpenAI API key is not configured. Please set the OPENAI_API_KEY environment variable.")
            return []
        
        # Initialize the OpenAI client
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.3,  # Lower temperature for more focused extraction
            openai_api_key=OPENAI_API_KEY
        )
        
        # Create a prompt template for extracting key points
        prompt_template = PromptTemplate(
            input_variables=["text", "max_points"],
            template="""
            Extract the {max_points} most important key points from the following text.
            Format each point as a bullet point starting with "- ".
            Focus on the main ideas, facts, and conclusions.
            
            TEXT:
            {text}
            
            KEY POINTS:
            """
        )
        
        # Prepare the prompt
        prompt = prompt_template.format(text=text, max_points=max_points)
        
        # Get the response from the model
        with st.spinner("Extracting key points..."):
            response = llm.invoke(prompt)
            
            # Extract the key points from the response
            key_points_text = response.content.strip()
            
            # Split into individual points
            key_points = [point.strip() for point in key_points_text.split('\n') if point.strip().startswith('-')]
            
            return key_points
    
    except Exception as e:
        st.error(f"Error extracting key points: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return []

# Main UI
st.title("🪄 NoticIA")
st.markdown("Transform complex reports into easy-to-understand articles")

# Add this code right after the function definitions and before the main app code
# Initialize session state variables if they don't exist
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'input_type' not in st.session_state:
    st.session_state.input_type = 'Text'
if 'report_text' not in st.session_state:
    st.session_state.report_text = None
if 'transformed_text' not in st.session_state:
    st.session_state.transformed_text = None
if 'audience' not in st.session_state:
    st.session_state.audience = 'general'
if 'url_value' not in st.session_state:
    st.session_state.url_value = ''
if 'last_action' not in st.session_state:
    st.session_state.last_action = None

# Add this line right after the NOTION_DATABASE_ID line (around line 40)
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")

# And make sure to extract it properly
NOTION_PAGE_ID = extract_notion_page_id(NOTION_PAGE_ID) if NOTION_PAGE_ID else ""

# Initialize Notion client if credentials are available
notion = None
if NOTION_API_KEY and NOTION_PAGE_ID:
    notion = Client(auth=NOTION_API_KEY)

# Initialize the Agent
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
tools = [
    Tool(
        name="SimplifyText",
        func=lambda text: transform_text(text, st.session_state.get('target_audience', 'general')),
        description="Transforms complex text into an easy-to-understand article."
    ),
    Tool(
        name="ExtractKeyPoints",
        func=extract_key_points,
        description="Extracts and organizes key points from the text."
    )
]
agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

# Step 1: Input Selection and Extraction
if st.session_state.step == 1:
    st.markdown("""
    <div class="step-header">
        <div class="step-number">1</div>
        <div class="step-title">Choose your input method</div>
    </div>
    """, unsafe_allow_html=True)

    # Replace the radio button code with this enhanced version
    st.markdown("### Choose your input method:")

    input_type = st.radio(
        "",  # Empty label since we're using the markdown header above
        options=["Text", "PDF", "Website URL"],
        index=["Text", "PDF", "Website URL"].index(st.session_state.input_type),
        horizontal=True,
        key="input_type_radio"
    )
    
    # Update session state if selection changes
    if input_type != st.session_state.input_type:
        st.session_state.input_type = input_type
        st.experimental_rerun()
    
    # Display the appropriate input method based on selection
    if input_type == "Text":
        st.subheader("📝 Enter your text")
        
        text_input = st.text_area(
            "Paste your report here:",
            height=300,
            placeholder="Enter your report text..."
        )
        
        if st.button("Extract Content", type="primary", disabled=not text_input):
            if text_input:
                st.session_state.report_text = text_input
                st.session_state.step = 2
                st.experimental_rerun()
            else:
                st.error("Please enter some text before proceeding.")
    
    elif input_type == "PDF":
        st.subheader("📄 Upload PDF")
        
        uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
        
        if st.button("Extract Content", type="primary", disabled=not uploaded_file):
            if uploaded_file:
                with st.spinner("Processing PDF..."):
                    extracted_text = extract_text_from_pdf(uploaded_file)
                    if extracted_text:
                        st.session_state.report_text = extracted_text
                        st.success("PDF processed successfully!")
                        with st.expander("Show extracted text"):
                            st.markdown(f"""
                            ```
                            {extracted_text[:1000] + ("..." if len(extracted_text) > 1000 else "")}
                            ```
                            """)
                        st.session_state.step = 2
                        st.experimental_rerun()
                    else:
                        st.error("Could not extract text from the PDF. Please try another file.")
    
    else:  # Website URL
        st.subheader("🔗 Enter website URL")
        
        url = st.text_input(
            "Enter website URL:", 
            value=st.session_state.get('url_value', ''),
            placeholder="https://example.com",
            help="Enter a full URL including http:// or https://"
        )
        
        st.session_state.url_value = url
        
        if st.button("Extract Content", type="primary", disabled=not url):
            if url:
                st.session_state.last_action = "url_extract"
                
                with st.spinner("Fetching content..."):
                    extracted_text = extract_text_from_url(url)
                    if extracted_text:
                        st.session_state.report_text = extracted_text
                        st.success("Content extracted successfully!")
                        with st.expander("Show extracted text"):
                            st.markdown(f"""
                            ```
                            {extracted_text[:1000] + ("..." if len(extracted_text) > 1000 else "")}
                            ```
                            """)
                        st.session_state.last_successful_url = url
                        st.session_state.step = 2
                        st.experimental_rerun()
                    else:
                        st.error("Could not extract content from the URL. Please try another URL or input method.")

# Step 2: Audience Selection
elif st.session_state.step == 2:
    st.markdown('<p class="section-header">Step 2: Select your target audience</p>', unsafe_allow_html=True)
    
    # Show a preview of the extracted text
    with st.expander("Show extracted content", expanded=False):
        st.markdown(f"""
        ```
        {st.session_state.report_text[:1000] + ("..." if len(st.session_state.report_text) > 1000 else "")}
        ```
        """)
    
    # Audience selection
    target_audience = st.select_slider(
        "Target audience",
        options=[
            "elementary",
            "high_school",
            "general",
            "business",
            "technical",
            "academic"
        ],
        value="general",
        format_func=lambda x: {
            "general": "General Public",
            "technical": "Technical Professionals",
            "academic": "Academic Audience",
            "business": "Business Professionals",
            "elementary": "Elementary School",
            "high_school": "High School"
        }[x],
        key='target_audience',
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Back to Input", use_container_width=True):
            st.session_state.step = 1
            st.experimental_rerun()
    
    with col2:
        if st.button("Transform", type="primary", use_container_width=True):
            with st.spinner("Transforming text with SAPTIVA..."):
                # Use SAPTIVA API to transform the text
                transformed_text = transform_text(st.session_state.report_text, target_audience)
                if transformed_text:
                    st.session_state.transformed_text = transformed_text
                    st.session_state.step = 3
                    st.experimental_rerun()
                else:
                    st.error("Failed to transform text. Please check your SAPTIVA API key and try again.")

# Step 3: Transformation and Output
elif st.session_state.step == 3:
    st.markdown('<p class="section-header">Step 3: Generating your article</p>', unsafe_allow_html=True)
    
    with st.spinner("Transforming your report..."):
        try:
            # Process the text from session state
            transformed_text = transform_text(st.session_state.report_text, st.session_state.audience)
            
            if transformed_text:
                st.session_state.transformed_text = transformed_text
                st.session_state.step = 4  # Move to results
                st.experimental_rerun()
            else:
                st.error("Failed to transform the text. Please try again with different content.")
                if st.button("← Back", use_container_width=True):
                    st.session_state.step = 2
                    st.experimental_rerun()
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            if st.button("← Back", use_container_width=True):
                st.session_state.step = 2
                st.experimental_rerun()

# Step 4: Results and Publishing
elif st.session_state.step == 4:
    st.markdown("""
    <div class="step-header">
        <div class="step-number">4</div>
        <div class="step-title">Your transformed article</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display the transformed article in a nicely styled container
    with st.container():
        st.markdown('<div class="article-container">', unsafe_allow_html=True)
        st.markdown(st.session_state.transformed_text)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Replace the export tabs section with this improved version
    st.markdown("""
    <div class="export-section-header">
        <span>📤 Export Options</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Change back to 3 columns
    export_col1, export_col2, export_col3 = st.columns(3)
    
    # PDF export
    with export_col1:
        st.markdown('<div class="export-card">', unsafe_allow_html=True)
        st.markdown('<h4>📄 Download as PDF</h4>', unsafe_allow_html=True)
        
        if st.button("Generate PDF", type="primary", use_container_width=True):
            try:
                # Create a temporary file for the PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    pdf_file = tmp.name
                
                # Create the PDF document
                doc = SimpleDocTemplate(
                    pdf_file,
                    pagesize=letter,
                    rightMargin=72,
                    leftMargin=72,
                    topMargin=72,
                    bottomMargin=72
                )
                
                # Define styles
                styles = getSampleStyleSheet()
                styles.add(ParagraphStyle(
                    name='Justify',
                    alignment=TA_JUSTIFY,
                    fontName='Helvetica',
                    fontSize=12,
                    spaceAfter=12
                ))
                
                # Create a list to hold the flowables
                flowables = []
                
                # Process the markdown text
                lines = st.session_state.transformed_text.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Handle headings
                    if line.startswith('# '):
                        # Title (H1)
                        title_text = line[2:].strip()
                        title_style = styles['Title']
                        flowables.append(Paragraph(title_text, title_style))
                        flowables.append(Spacer(1, 12))
                    elif line.startswith('## '):
                        # Heading (H2)
                        heading_text = line[3:].strip()
                        heading_style = styles['Heading2']
                        flowables.append(Paragraph(heading_text, heading_style))
                        flowables.append(Spacer(1, 10))
                    elif line.startswith('### '):
                        # Subheading (H3)
                        subheading_text = line[4:].strip()
                        subheading_style = styles['Heading3']
                        flowables.append(Paragraph(subheading_text, subheading_style))
                        flowables.append(Spacer(1, 8))
                    elif line.startswith('- ') or line.startswith('* '):
                        # Bullet point
                        bullet_text = line[2:].strip()
                        bullet_style = styles['Normal']
                        flowables.append(Paragraph(f"• {bullet_text}", bullet_style))
                        flowables.append(Spacer(1, 6))
                    elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
                        # Numbered list
                        number_text = line[line.find('.')+1:].strip()
                        number_style = styles['Normal']
                        list_number = line[:line.find('.')].strip()
                        flowables.append(Paragraph(f"{list_number}. {number_text}", number_style))
                        flowables.append(Spacer(1, 6))
                    elif line == '':
                        # Empty line
                        flowables.append(Spacer(1, 12))
                    else:
                        # Regular paragraph
                        paragraph_style = styles['Normal']
                        flowables.append(Paragraph(line, paragraph_style))
                        flowables.append(Spacer(1, 8))
                    
                    i += 1
                
                # Build the PDF
                doc.build(flowables)
                
                with open(pdf_file, "rb") as f:
                    pdf_bytes = f.read()
                
                # Extract title from the content
                lines = st.session_state.transformed_text.split('\n')
                title = "Transformed Article"  # default title
                for line in lines:
                    if line.strip().startswith('#'):
                        # Remove '#' symbols and whitespace
                        title = line.lstrip('#').strip()
                        break
                
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=f"{title}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # Clean up the temporary file
                os.unlink(pdf_file)
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Markdown export
    with export_col2:
        st.markdown('<div class="export-card">', unsafe_allow_html=True)
        st.markdown('<h4>📝 Download as Markdown</h4>', unsafe_allow_html=True)
        
        # Extract title from the content
        lines = st.session_state.transformed_text.split('\n')
        title = "Transformed Article"  # default title
        for line in lines:
            if line.strip().startswith('#'):
                # Remove '#' symbols and whitespace
                title = line.lstrip('#').strip()
                break
        
        st.download_button(
            label="Download Markdown",
            data=st.session_state.transformed_text,
            file_name=f"{title}.md",
            mime="text/markdown",
            use_container_width=True
        )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Google Drive export
    with export_col3:
        st.markdown('<div class="export-card">', unsafe_allow_html=True)
        st.markdown('<h4>📤 Publish to Google Drive</h4>', unsafe_allow_html=True)
        
        # Add a note about wkhtmltopdf and public access
        st.markdown("""
        <div style="font-size: 0.8em; color: #666;">
        For best PDF quality, install <a href="https://wkhtmltopdf.org/downloads.html" target="_blank">wkhtmltopdf</a><br>
        Note: Published files will be accessible to anyone with the link
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Publish to Drive", type="primary", use_container_width=True):
            with st.spinner("Publishing to Google Drive..."):
                # Extract title from the content
                lines = st.session_state.transformed_text.split('\n')
                title = "Transformed Article"  # default title
                for line in lines:
                    if line.strip().startswith('#'):
                        # Remove '#' symbols and whitespace
                        title = line.lstrip('#').strip()
                        break
                        
                file_url = publish_to_drive(st.session_state.transformed_text, title)
                if file_url:
                    st.success("Published to Google Drive! The file is accessible to anyone with the link.")
                    st.markdown(f"""
                    <a href="{file_url}" target="_blank" style="display: inline-block; padding: 8px 16px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; margin-top: 10px;">
                        <span style="vertical-align: middle;">View Document</span>
                        <span style="vertical-align: middle; margin-left: 5px;">↗</span>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Failed to publish to Google Drive. Please check your API credentials.")

    # LinkedIn post export
    export_col4, export_col5 = st.columns(2)

    with export_col4:
        st.markdown('<div class="export-card">', unsafe_allow_html=True)
        st.markdown('<h4>🔗 Generar Post para LinkedIn</h4>', unsafe_allow_html=True)
        
        if st.button("Crear Publicación LinkedIn", type="primary", use_container_width=True):
            if "transformed_text" in st.session_state:
                try:
                    # Inline LinkedIn post generation
                    content = st.session_state.transformed_text
                    
                    # Validate API key
                    if not SAPTIVA_API_KEY or not SAPTIVA_API_KEY.startswith('va-ai-'):
                        st.warning("Invalid or missing SAPTIVA API key for LinkedIn post generation.")
                    else:
                        # Set up the headers
                        headers = {
                            "Authorization": f"Bearer {SAPTIVA_API_KEY}",
                            "Content-Type": "application/json"
                        }
                        
                        # Create a prompt for LinkedIn post generation
                        prompt = f"""
                        Genera 3 opciones de publicación para LinkedIn en español basadas en el siguiente contenido. 
                        
                        Sigue estas pautas:
                        1. Usa un estilo dinámico, atractivo e informal pero profesional
                        2. Incorpora emojis relevantes al inicio de párrafos y para enfatizar puntos clave
                        3. Utiliza un tono conversacional y personal
                        4. Incluye una llamada a la acción al final
                        5. Mantén cada publicación entre 150-250 palabras
                        6. Asegúrate que cada opción tenga un enfoque ligeramente diferente
                        7. Numera las opciones como "Opción 1:", "Opción 2:" y "Opción 3:"
                        8. Al final de cada publicación, incluye la frase "Fuente original: {st.session_state.get('original_url', '')}" si hay una URL disponible
                        
                        Contenido original:
                        {content}
                        """
                        
                        # Prepare the payload
                        payload = {
                            "modelName": "LLaMa3.3 70B",
                            "newTokens": 500,
                            "temperature": 0.9,
                            "sysPrompt": """Eres un experto en crear publicaciones atractivas para LinkedIn en español.
                            
Tu estilo es dinámico, atractivo e informal pero profesional. Incorporas emojis de manera estratégica 
para enfatizar puntos clave y al inicio de párrafos. Tu tono es conversacional y personal, 
transmitiendo entusiasmo y conocimiento profesional.

Tus publicaciones siempre incluyen:
1. Emojis relevantes al tema
2. Lenguaje natural y humanizado
3. Un tono que resuena con audiencias profesionales
4. Una llamada a la acción clara al final
5. Hashtags relevantes (2-4 máximo)

Adapta el contenido para que sea personal, mostrando insights profesionales y conocimiento 
de la industria. Cada publicación debe sentirse como escrita por un humano entusiasta 
que quiere compartir conocimiento valioso.""",
                            "message": prompt
                        }
                        
                        # Make the API request
                        with st.spinner("Generando opciones de publicación para LinkedIn..."):
                            response = requests.post(
                                "https://api-dev.saptiva.com/v1/chat/completions",
                                headers=headers,
                                json=payload,
                                timeout=30
                            )
                            
                            # Check if the request was successful
                            if response.status_code == 200:
                                result = response.json()
                                if "response" in result:
                                    st.session_state.linkedin_posts = result["response"]
                                else:
                                    # Create a simple default post if API fails
                                    lines = content.split('\n')
                                    title = ""
                                    for line in lines:
                                        if line.startswith('# '):
                                            title = line.replace('# ', '')
                                            break
                                    
                                    st.session_state.linkedin_posts = f"""
Opción 1:
✨ ¡Nuevo artículo sobre {title}! 📚

¿Qué opinas sobre este tema? Me encantaría conocer tu perspectiva. 
¡Comenta abajo y comparte con tu red si te pareció interesante! 👇 #Conocimiento #Aprendizaje

Opción 2:
🔍 Explorando: {title}

He sintetizado información clave sobre este tema tan relevante hoy en día.

¿Te interesa saber más? Envíame un mensaje directo y conversemos. 💬 #Profesional #Crecimiento

Opción 3:
💡 {title} - Un tema que todo profesional debería conocer

Acabo de publicar un resumen con los puntos más importantes.

¿Quieres profundizar en este tema? ¡Comparte tu experiencia en los comentarios! 🚀 #Desarrollo #Innovación
"""
                            else:
                                st.error(f"Error al generar publicaciones para LinkedIn: {response.status_code} - {response.text}")
                                
                                # Create a simple default post if API fails
                                lines = content.split('\n')
                                title = ""
                                for line in lines:
                                    if line.startswith('# '):
                                        title = line.replace('# ', '')
                                        break
                                
                                st.session_state.linkedin_posts = f"""
Opción 1:
✨ ¡Nuevo artículo sobre {title}! 📚

¿Qué opinas sobre este tema? Me encantaría conocer tu perspectiva. 
¡Comenta abajo y comparte con tu red si te pareció interesante! 👇 #Conocimiento #Aprendizaje

Opción 2:
🔍 Explorando: {title}

He sintetizado información clave sobre este tema tan relevante hoy en día.

¿Te interesa saber más? Envíame un mensaje directo y conversemos. 💬 #Profesional #Crecimiento

Opción 3:
💡 {title} - Un tema que todo profesional debería conocer

Acabo de publicar un resumen con los puntos más importantes.

¿Quieres profundizar en este tema? ¡Comparte tu experiencia en los comentarios! 🚀 #Desarrollo #Innovación
"""
                
                except Exception as e:
                    st.error(f"Error generando publicaciones para LinkedIn: {str(e)}")

    # Display LinkedIn posts if they exist
    if "linkedin_posts" in st.session_state:
        st.markdown("### Opciones de Publicación para LinkedIn")
        st.markdown('<div class="linkedin-posts-container">', unsafe_allow_html=True)
        
        linkedin_posts = st.session_state.linkedin_posts
        
        # Add copy buttons for each post
        posts = linkedin_posts.split("Opción")
        
        for i, post in enumerate(posts):
            if i == 0:  # Skip the first empty split
                continue
            
            post_content = f"Opción{post.strip()}"
            
            with st.expander(f"Opción {i}", expanded=i==1):
                st.markdown(post_content)
                
                # Obtener el contenido del post limpio (sin "Opción X:")
                clean_post = post.strip()
                
                # Agregar la URL original si existe
                original_url = st.session_state.get('original_url', '')
                if original_url and "Fuente original:" not in clean_post:
                    clean_post += f"\n\nFuente original: {original_url}"
                
                # Crear un contenedor para el botón de copiar con mejor diseño
                copy_container = st.container()
                
                # Usar un botón más atractivo
                if st.button("📋 Copiar al portapapeles", 
                            key=f"copy_linkedin_{i}", 
                            type="primary",
                            use_container_width=True):
                    
                    # Guardar en el estado de la sesión
                    st.session_state[f"copy_text_{i}"] = clean_post
                    st.session_state[f"copied_{i}"] = True
                    
                    # Escapar caracteres especiales para JavaScript
                    escaped_post = clean_post.replace('\\', '\\\\').replace('`', '\\`').replace("'", "\\'").replace('"', '\\"')
                    
                    # Crear el código JavaScript sin usar f-string para la parte problemática
                    js_code = """
                    <script>
                        const el = document.createElement('textarea');
                        el.value = `""" + escaped_post + """`;
                        document.body.appendChild(el);
                        el.select();
                        document.execCommand('copy');
                        document.body.removeChild(el);
                    </script>
                    """
                    st.markdown(js_code, unsafe_allow_html=True)
                
                # Mostrar mensaje de confirmación y área de texto solo si se ha copiado
                if st.session_state.get(f"copied_{i}", False):
                    st.success("✅ ¡Copiado al portapapeles!")
                    
                    # Mostrar el texto en un área de texto directamente (sin expander anidado)
                    st.text_area(
                        "Texto copiado (selecciona y copia manualmente si es necesario):",
                        st.session_state[f"copy_text_{i}"],
                        height=150,
                        key=f"manual_copy_{i}"
                    )
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Add a button to start over
    st.markdown("<hr/>", unsafe_allow_html=True)
    if st.button("← Start Over", use_container_width=True):
        st.session_state.step = 1
        st.session_state.report_text = None
        st.session_state.transformed_text = None
        st.experimental_rerun()

# Sidebar content
with st.sidebar:
    st.markdown("""
    ### About
    
    Transform complex reports into easy-to-understand articles using AI.
    
    ### Features
    
    - Multiple input formats (Text, PDF, URL)
    - Audience-specific language
    - Key points extraction
    - Markdown formatting
    - Google Drive integration
    
    ### Tips
    
    1. Choose the right audience level
    2. For PDFs, ensure they're text-based
    3. For URLs, use direct article links
    4. Review extracted text before transforming
    """)

# Add a debug expander in the sidebar (you can remove this later)
with st.sidebar:
    with st.expander("Debug Info", expanded=False):
        st.write("Session State:")
        st.write(f"- Step: {st.session_state.get('step')}")
        st.write(f"- Input Type: {st.session_state.get('input_type')}")
        st.write(f"- Last Action: {st.session_state.get('last_action')}")
        st.write(f"- URL Value: {st.session_state.get('url_value')}")
        
        if st.button("Reset Session"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.experimental_rerun() 

def transform_with_saptiv(content, target_audience, tone, format_type, max_tokens=2000):
    """Transform content using the Saptiv API"""
    try:
        # Prepare the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('SAPTIV_API_KEY')}"
        }
        
        # Construct your prompt
        prompt = f"""Transform the following content into a clear, structured summary for a {target_audience} audience using a {tone} tone.

Format your response exactly as follows:
1. Start with a concise, descriptive title using # format
2. Provide a brief introduction (1-2 sentences)
3. List 3-5 key points as bullet points (using - format)
4. List key indicators or metrics as bullet points (using - format)
5. Include a condensed summary paragraph that captures the most important elements
6. End with 2-3 actionable recommendations (if applicable)

Original content:
{content}
"""
        
        # Prepare the request payload with max_tokens parameter
        payload = {
            "model": "LLaMa3.3 70B",  # Replace with the actual model name
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that transforms content into a."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 1024,  # Remove the comma in 1,024
            "temperature": 0.7
        }
        
        # Make the API call
        response = requests.post(
            "https://api-dev.saptiva.com/v1/chat/completions",  # Fixed URL
            headers=headers,
            json=payload
        )
        
        # Parse the response
        if response.status_code == 200:
            result = response.json()
            
            # Extract token usage information if available
            token_usage = result.get("usage", {})
            input_tokens = token_usage.get("prompt_tokens", 0)
            output_tokens = token_usage.get("completion_tokens", 0)
            total_tokens = token_usage.get("total_tokens", 0)
            
            # Log token usage
            print(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
            # Return the result
            return {
                "output": result["choices"][0]["message"]["content"],
                "token_usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                }
            }
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        st.error(f"Error transforming content: {str(e)}")
        return None

# You can then call this function with different max_tokens values
def process_content():
    if st.button("Transform"):
        with st.spinner("Transforming content..."):
            # Get the content and parameters
            content = st.session_state.report_text
            target_audience = st.session_state.target_audience
            tone = st.session_state.tone
            format_type = st.session_state.format_type
            
            # You can adjust max_tokens based on content length or user selection
            content_length = len(content)
            if content_length > 10000:
                max_tokens = 4000  # More tokens for longer content
            else:
                max_tokens = 2000  # Default for shorter content
                
            # Call the transform function with max_tokens
            result = transform_with_saptiv(
                content, 
                target_audience, 
                tone, 
                format_type,
                max_tokens=max_tokens
            )
            
            if result:
                st.session_state.result = result
                st.experimental_rerun() 

# Move the LinkedIn post generator function to the top of your file
# Add it right after the transform_text_with_saptiva function (around line 300)

def generate_linkedin_post(content):
    """Generate LinkedIn post options based on the transformed content"""
    try:
        # Validate API key
        if not SAPTIVA_API_KEY or not SAPTIVA_API_KEY.startswith('va-ai-'):
            st.warning("Invalid or missing SAPTIVA API key for LinkedIn post generation.")
            return None
        
        # Set up the headers
        headers = {
            "Authorization": f"Bearer {SAPTIVA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Create a prompt for LinkedIn post generation
        prompt = f"""
        Genera 3 opciones de publicación para LinkedIn en español basadas en el siguiente contenido. 
        
        Sigue estas pautas:
        1. Usa un estilo dinámico, atractivo e informal pero profesional
        2. Incorpora emojis relevantes al inicio de párrafos y para enfatizar puntos clave
        3. Utiliza un tono conversacional y personal
        4. Incluye una llamada a la acción al final
        5. Mantén cada publicación entre 150-250 palabras
        6. Asegúrate que cada opción tenga un enfoque ligeramente diferente
        7. Numera las opciones como "Opción 1:", "Opción 2:" y "Opción 3:"
        8. Al final de cada publicación, incluye la frase "Fuente original: {st.session_state.get('original_url', '')}" si hay una URL disponible
        
        Contenido original:
        {content}
        """
        
        # Prepare the payload
        payload = {
            "modelName": "LLaMa3.3 70B",
            "newTokens": 1000,
            "temperature": 0.9,
            "sysPrompt": """Eres un experto en crear publicaciones atractivas para LinkedIn en español.
            
Tu estilo es dinámico, atractivo e informal pero profesional. Incorporas emojis de manera estratégica 
para enfatizar puntos clave y al inicio de párrafos. Tu tono es conversacional y personal, 
transmitiendo entusiasmo y conocimiento profesional.

Tus publicaciones siempre incluyen:
1. Emojis relevantes al tema
2. Lenguaje natural y humanizado
3. Un tono que resuena con audiencias profesionales
4. Una llamada a la acción clara al final
5. Hashtags relevantes (2-4 máximo)

Adapta el contenido para que sea personal, mostrando insights profesionales y conocimiento 
de la industria. Cada publicación debe sentirse como escrita por un humano entusiasta 
que quiere compartir conocimiento valioso.""",
            "message": prompt
        }
        
        # Make the API request
        with st.spinner("Generando opciones de publicación para LinkedIn..."):
            response = requests.post(
                "https://api-dev.saptiva.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                result = response.json()
                if "response" in result:
                    linkedin_posts = result["response"]
                    return linkedin_posts
                else:
                    return "No se pudieron generar publicaciones para LinkedIn. Por favor, intenta de nuevo."
            else:
                return "Error al generar publicaciones para LinkedIn. Por favor, intenta de nuevo."
    
    except Exception as e:
        st.error(f"Error generando publicaciones para LinkedIn: {str(e)}")
        return None

# Add this to your CSS section
st.markdown("""
    <style>
    /* Existing CSS... */
    
    /* LinkedIn Posts Container */
    .linkedin-posts-container {
        margin-top: 20px;
        background-color: #F9FAFB;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
    }
    
    /* LinkedIn Post Option */
    .streamlit-expanderHeader {
        background-color: #0A66C2;
        color: white !important;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin-bottom: 10px;
    }
    
    /* Copy Button */
    button[key^="copy_linkedin_"] {
        background-color: #0A66C2;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        cursor: pointer;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Add this local fallback function
def generate_linkedin_posts_locally(content):
    """Generate LinkedIn posts locally when the API fails"""
    # Extract title and first paragraph for a simple post
    lines = content.split('\n')
    title = ""
    intro = ""
    
    for line in lines:
        if line.startswith('# '):
            title = line.replace('# ', '')
            break
    
    # Find first paragraph after title
    found_title = False
    for line in lines:
        if found_title and line.strip() and not line.startswith('#'):
            intro = line
            break
    
    # Create three simple LinkedIn post options
    return f"""
Opción 1:
✨ ¡Nuevo artículo sobre {title}! 📚

{intro[:100]}...

¿Qué opinas sobre este tema? Me encantaría conocer tu perspectiva. 
¡Comenta abajo y comparte con tu red si te pareció interesante! 👇 #Conocimiento #Aprendizaje

Opción 2:
🔍 Explorando: {title}

He sintetizado información clave sobre este tema tan relevante hoy en día.

¿Te interesa saber más? Envíame un mensaje directo y conversemos. 💬 #Profesional #Crecimiento

Opción 3:
💡 {title} - Un tema que todo profesional debería conocer

Acabo de publicar un resumen con los puntos más importantes.

¿Quieres profundizar en este tema? ¡Comparte tu experiencia en los comentarios! 🚀 #Desarrollo #Innovación
""" 