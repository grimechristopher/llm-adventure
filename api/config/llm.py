import os
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from utils.logging import get_logger

logger = get_logger(__name__)


# Use a factory functions to create LLM instances

def create_lmstudio_qwen2_5_14b_instruct_llm():
    logger.info("Creating LM Studio Qwen2.5-14B-Instruct LLM")
    return ChatOpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="not-used",
        model="qwen2.5-14b-instruct",
        temperature=0.7
    )

def create_azure_one_gpt4o_llm():
    logger.info("Creating Azure One GPT-4o LLM")
    
    # Log configuration details for debugging
    logger.debug("Azure One config", 
        endpoint=os.getenv("AZURE_ONE_OPENAI_API_URL", "Not set"),
        deployment=os.getenv("AZURE_ONE_OPENAI_DEPLOYMENT_NAME", "Not set"),
        api_version=os.getenv("AZURE_ONE_OPENAI_API_VERSION", "Not set"),
        api_key_configured=bool(os.getenv("AZURE_ONE_OPENAI_API_KEY"))
    )
    
    return AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_ONE_OPENAI_API_URL"),
        api_key=os.getenv("AZURE_ONE_OPENAI_API_KEY"),
        azure_deployment=os.getenv("AZURE_ONE_OPENAI_DEPLOYMENT_NAME"),
        api_version=os.getenv("AZURE_ONE_OPENAI_API_VERSION"),
        temperature=0.7
    )


# Create a registry of available LLM configurations
LLM_REGISTRY = {
    "lm_studio": create_lmstudio_qwen2_5_14b_instruct_llm,
    "azure_one": create_azure_one_gpt4o_llm,
}

# Function to initialize all the llms
def initialize_llms():
    logger.info("Starting LLM initialization")
    llms = {}
    
    for llm_name, llm_factory in LLM_REGISTRY.items():
        try:
            llms[llm_name] = llm_factory()
            logger.info(f"Successfully initialized {llm_name}")
        except Exception as e:
            logger.error(f"Failed to initialize {llm_name}", error=e, llm_name=llm_name)
            # Continue with other LLMs even if one fails
            continue
    
    logger.info("LLM initialization complete", successfully_loaded=list(llms.keys()))
    
    if not llms:
        logger.error("No LLMs were successfully initialized!")
        
    return llms