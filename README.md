# Report Transformer

A Flask-based API that transforms complex reports into easy-to-understand articles using AI.

## Features

- Transforms complex reports into clear, engaging articles
- Customizable target audience
- Extracts and organizes key points
- Returns content in markdown format
- Maintains key information while simplifying language

## Setup

1. Clone this repository
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Add your OpenAI API key to `.env`:
   - Get your API key from [OpenAI Dashboard](https://platform.openai.com/api-keys)
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the application:
   ```bash
   python app.py
   ```

## API Usage

### Transform Report

**Endpoint:** `POST /transform`

**Request Body:**
```json
{
    "text": "Your report text here",
    "target_audience": "general" // optional, defaults to "general"
}
```

**Response:**
```json
{
    "transformed_article": "Markdown formatted article..."
}
```

## Target Audience Options

- "general" - For general public
- "technical" - For technical professionals
- "academic" - For academic audience
- "business" - For business professionals
- "elementary" - For elementary school students
- "high_school" - For high school students

## License

MIT License

Copyright (c) 2024

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE. 