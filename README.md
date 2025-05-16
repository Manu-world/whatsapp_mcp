# WhatsApp Agent with Google Drive Integration

A powerful WhatsApp bot that integrates with Google Drive through a Model-Control-Protocol (MCP) server, allowing users to interact with their Google Drive files using natural language commands.

## Features

- **Natural Language Interface**: Interact with Google Drive using plain English
- **File Management**: List, search, and manage files in Google Drive
- **Document Analysis**: Read, parse, and analyze document contents
- **Information Extraction**: Extract key information from documents
- **Question Answering**: Get answers to questions about document contents
- **WhatsApp Integration**: Access all features through WhatsApp messaging

## Prerequisites

- Python 3.8+
- OpenAI API key
- Google Cloud credentials
- oauth2client<4.0.0 (required for Google Drive API file cache support)

## Installation

1. Clone the repository:

  ```bash
  git clone https://github.com/yourusername/whatsapp_agent.git
  cd whatsapp_agent
  ```

2. Install Python dependencies:

  ```bash
  pip install -r requirements.txt
  ```

3. Set up environment variables:

  ```bash
  cp .env.example .env
  ```

Edit the `.env` file with your credentials:

```
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=path_to_your_google_credentials.json
WHATSAPP_API_KEY=your_whatsapp_api_key
```

## Project Structure

```
whatsapp_agent/
├── app/
│   ├── api/
│   │   └── webhook.py
│   ├── service/
│   │   └── agent_service.py
│   └── main.py
├── gdrive_mcp/
│   ├── server/
│   │   ├── agent.py
│   │   └── drive_mcp_server.py
│   └── tools/
│       ├── file_browsing_tools.py
│       └── file_content_tools.py
├── requirements.txt
└── README.md
```

## Usage

1. Start the Google Drive MCP server:

```bash
python -m gdrive_mcp.server.drive_mcp_server
```

2. Start the WhatsApp agent server:

```bash
python -m app.main
```

3. Send messages to your WhatsApp bot to interact with Google Drive:

  ```bssh
  - "List all my files in Google Drive"
  - "Search for documents about project X"
  - "Read the contents of my latest report"
  - "Summarize the meeting notes from last week"
  - "What are the key points in the project proposal?"
  ```

## Available Commands

The bot supports various commands for Google Drive operations:

- **File Browsing**:
  - List all files
  - List files in a specific folder
  - Search for files by name or content
  - Get file metadata

- **Document Analysis**:
  - Read file contents
  - Parse documents into sections
  - Extract key information
  - Create document summaries
  - Search within documents
  - Answer questions about content

## Development

### Adding New Tools

To add new tools to the Google Drive agent:

1. Create a new tool class in the appropriate tools directory
2. Register the tool in `gdrive_mcp/server/agent.py`
3. Update the tool documentation in `drive_mcp_server.py`

### Testing

Run the test suite:

```bash
python -m pytest
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for the GPT models
- Google for the Drive API
- WhatsApp for the Business API
- The LangChain and LangGraph teams for their amazing frameworks

## Troubleshooting

### Common Issues

1. **File Cache Warning**

   ```bash
   file_cache is only supported with oauth2client<4.0.0
   ```

   Solution: Ensure you have the correct version of oauth2client installed:

   ```bash
   pip install "oauth2client<4.0.0"
   ```

2. **Google Drive API Authentication**
   - Make sure your Google Cloud credentials file is properly set up
   - Verify the `GOOGLE_APPLICATION_CREDENTIALS` environment variable points to the correct file
   - Ensure the service account has the necessary Drive API permissions

3. **OpenAI API Issues**
   - Verify your OpenAI API key is valid and has sufficient credits
   - Check that the model name in the configuration matches your OpenAI subscription

4. **WhatsApp Integration**
   - Ensure your WhatsApp Business API credentials are valid
   - Verify the webhook URL is correctly configured in your WhatsApp Business settings
   - Check that the server is accessible from the internet for webhook callbacks

[![Build Status](https://github.com/RGT-DevOps/google-drive-mcp/actions/workflows/main.yml/badge.svg)](https://github.com/RGT-DevOps/google-drive-mcp/actions/workflows/main.yml)
