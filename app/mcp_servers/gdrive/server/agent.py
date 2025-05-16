from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory

# Create LangChain agent
from app.mcp_servers.gdrive.tools.file_browsing_tools import ListAllFilesTool,SearchFilesTool, GetFileMetadataTool, ListFolderFilesTool, UploadFileToDriveTool
from app.mcp_servers.gdrive.tools.file_content_tools import ReadFileTool, ExtractInfoTool, ParseDocumentTool, AnswerQuestionTool, SearchInDocumentTool, SummarizeDocumentTool
import os
from dotenv import load_dotenv

load_dotenv()


def create_drive_agent():
    # Define tools
    tools = [
        ListAllFilesTool(),
        ListFolderFilesTool(),
        SearchFilesTool(),
        GetFileMetadataTool(),
        ReadFileTool(),
        ParseDocumentTool(),
        ExtractInfoTool(),
        SummarizeDocumentTool(),
        SearchInDocumentTool(),
        AnswerQuestionTool(),
        UploadFileToDriveTool()
    ]

    # Create OpenAI-based agent
    llm = ChatOpenAI(model="gpt-4o", temperature=0.2, api_key=os.getenv("OPENAI_API_KEY"))
    
    # Define a system message that explains what the agent does
    system_message = """You are DriveAssistant, an AI agent specialized in managing Google Drive files.
You have tools to browse files, search for specific content, retrieve metadata, read and analyze documents.
For document analysis, you can read files, parse them into sections, extract key information, summarize content,
search inside documents, and answer questions about their contents.

Follow these steps when analyzing documents:
1. First use the search_file tool to search for specific document(s) based on necessary filters to access its content
2. Then use the appropriate tool based on what the user needs:
   - Use parse_document to break down document structure
   - Use extract_information to identify dates, names, emails, etc.
   - Use summarize_document to get the gist of the document
   - Use search_in_document to find specific information
   - Use answer_question to answer specific questions about the content
   - Use upload_file_to_drive to Upload a local file to Google Drive. Optionally specify a folder to upload into.

Always provide helpful responses about file operations and guide users through their Google Drive interactions."""
    
    # Create a prompt template with the system message and placeholders for messages and agent scratchpad
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Create memory for the agent
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    # Create the agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # Create the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor

# if __name__ == "__main__":
#     # Create and run the Drive agent
#     drive_agent = create_drive_agent()
    
#     print("Welcome to DriveAssistant! How can I help you with your Google Drive today?")
    
#     while True:
#         user_input = input("\nYou: ")
#         if user_input.lower() in ['exit', 'quit', 'bye']:
#             print("DriveAssistant: Goodbye!")
#             break
        
#         try:
#             response = drive_agent.invoke({"input": user_input})
#             print(f"\nDriveAssistant: {response['output']}")
#         except Exception as e:
#             print(f"\nDriveAssistant: I encountered an error: {str(e)}")