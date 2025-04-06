import datetime
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.types import HttpOptions
from dotenv import load_dotenv
from google.genai.types import FunctionDeclaration, GenerateContentConfig, Tool, GoogleSearch
from .hcdp import request_from_params
import os

# Load environment variables from .env file
load_dotenv()

# Get project ID and location from environment variables
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")

client = genai.Client(
    vertexai=True,
    http_options=HttpOptions(api_version="v1"),
    project=PROJECT_ID,
    location=LOCATION,
)
model = "gemini-2.0-flash-001"

with open("hcdp_API.txt", "r") as file:
    text = file.read()

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message] = []

class ChatResponse(BaseModel):
    response: str


def get_tools():

    get_variable_info = FunctionDeclaration(
        name="get_variable_info",
        description="Get the climate variable",
        parameters={
            "type": "OBJECT",
            "properties": {
                "variable_name": {"type": "STRING", "description": "Climate variable the user is interested in"},
            },
        },
    )

    get_time_slice = FunctionDeclaration(
        name="get_time_slice",
        description="Get the time slice",
        parameters={
            "type": "OBJECT",
            "properties": {
                "start_time": {"type": "STRING", "description": "Start time for the time slice"},
                "end_time": {"type": "STRING", "description": "End time for the time slice"},
            },
        },
    )

    get_time_resolution = FunctionDeclaration(
        name="get_time_resolution",
        description="Get the time resolution",
        parameters={
            "type": "OBJECT",
            "properties": {
                "resolution": {"type": "STRING", "description": "Time resolution for the data (daily, monthly)"},
            },
        },
    )

    get_named_location = FunctionDeclaration(
        name="get_named_location",
        description="Get the name location",
        parameters={
            "type": "OBJECT",
            "properties": {
                "location_name": {"type": "STRING", "description": "Extract the location name from the user query"},
            },
        },
    )

    get_api_parameters = FunctionDeclaration(
        name="get_api_parameters",
        description="Get the API parameters",
        parameters={
            "type": "OBJECT",
            "properties": {
                "time_start": {"type": "STRING", "description": "Start time for the API request in ISO-8601 format"},
                "time_end": {"type": "STRING", "description": "End time for the API request in ISO-8601 format"},
                "location": {"type": "STRING", "description": "Location for the API request"},
                "lat": {"type": "NUMBER", "description": "Latitude for the API request"},
                "lng": {"type": "NUMBER", "description": "Longitude for the API request"},
                "datatype": {"type": "STRING", "description": "Variable requested. Rainfall or temperature"},
                "period": {"type": "STRING", "description": "Time resolution of the request. Day or month"},
                "aggregation": {"type": "STRING", "description": "Aggregation type for temperature. Min, max, mean"},
                "is_region": {"type": "BOOLEAN", "description": "Is the location a region?"},
            },
        },
    )


    tools = Tool(
        function_declarations=[
            # get_variable_info,
            # get_time_slice,
            # get_time_resolution,
            # get_named_location,
            get_api_parameters
        ],
    )

    return [tools]

# make an endpoint to provide a random interesting fact about the hawaiian island provided by the user
@app.get("/funfact")
async def funfact_endpoint(request: Request):
    """
    Endpoint to provide a random interesting fact about the Hawaiian island provided by the user.
    """
    island = request.query_params.get("island")
    if not island:
        raise HTTPException(status_code=400, detail="Please provide an island name.")

    response = client.models.generate_content(
        model=model,
        contents=types.Content(
            role="user", parts=[types.Part(text=f"Tell me a fun, interesting fact about {island}.")]
        ),
        config=GenerateContentConfig(
            system_instruction=f"""
            You are a Hawaii Data Climate Portal AI assistant that provides fun facts about the Hawaiian islands.
            Provide a fun fact about {island}. Only return the fact, do not say here is a fun fact.
            Search on the web for updated, interesting facts about the island weather, construction and history, and anything interesting about it.
            Make it one sentences long, no more than 20 words, no line breaks.
            """,
            temperature=2,
            tools=[
                Tool(google_search=GoogleSearch()),
            ]                
            )
        )
    if response.candidates and response.candidates[0].content.parts:
        return {"response": response.candidates[0].content.parts[0].text}
    else:
        raise HTTPException(
            status_code=500, detail="Failed to get a valid response from the model."
        )

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that interacts with the Gemini Pro model via Vertex AI.
    """
    if model is None:
        raise HTTPException(
            status_code=503, detail="Vertex AI integration is not enabled."
        )

    try:
        if not request.messages:
            raise HTTPException(
                status_code=400, detail="Please provide at least one message."
            )

        prompt = request.messages[-1].content
        tools = get_tools()

        today = datetime.datetime.now().isoformat()

        contents = [
            types.Content(
                role="user", parts=[types.Part(text=prompt)]
            ),
        ]

        request_builder = client.models.generate_content(
            model=model,
            contents=contents,
            config=GenerateContentConfig(
                temperature=0,
                tools=tools,
                # system_instruction=f"""
                # Today is {today}.
                # You are a Hawaii Data Climate Portal API assistant to help query the data.
                # The user will ask questions and your job is to generate the API call to the Hawaii Data Climate Portal API.
                # The API call should be based on the user's question, so the returned data can be used to make a plot.
                # If the information is not complete for the API request, fill in the missing information with the best guess, including lat/lng.
                # Include production=new for rainfall and skip it for temperature.
                # Include the aggregation type for temperature based on the following values: min, max, mean. Infer the aggregation type from the user question.
                # Do not forget to include the period for the requested data (day or month). If not included, use month.
                # The data range goes from 1990 to {today}. Time has to be in ISO-8601 format.
                # If the user does not specify the time range, use the whole range.
                # All the requests are Hawaii specific, so you can assume the user is asking about Hawaii. Always return extend=statewide, and include lat/lng.
                # The API documentation is available at: 
                
                # {text}.

                # The API url always needs to be included: https://api.hcdp.ikewai.org
                # Reply with the API only, do not include any other text.
                # """
                system_instruction=f"""
                Today is {today}.
                You are a Hawaii Data Climate Portal API assistant to help query the data.
                The user will ask questions and your job is to extract the parameters from the user question to generate the request to the Hawaii Data Climate Portal API.
                
                """
                ),
        )

        function_call = request_builder.candidates[0].content.parts[0].function_call if request_builder.candidates and request_builder.candidates[0].content.parts else None

        extra_params = None

        if function_call:
            print("Function call detected")
            hdcp_response = await request_from_params(
                function_call.args
            )
            extra_params = hdcp_response.get("extra_params", None)
            print("HDCP response:", hdcp_response)
            if hdcp_response is None:
                raise HTTPException(
                    status_code=500, detail="Failed to get a valid response from the HDCP API."
                )
            hdcp_response_part = types.Part.from_function_response(
                name=function_call.name,
                response={"results": hdcp_response.get("data", None)},
            )

            contents.append(types.Content(role="model", parts=[types.Part(function_call=function_call)]))
            contents.append(types.Content(role="user", parts=[hdcp_response_part]))

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=GenerateContentConfig(
                    tools=tools.append(Tool(google_search=GoogleSearch())),
                    system_instruction=f"""
                    Today is {today}.
                    You are a Hawaii Data Climate Portal AI assistant that helps users with hawaii climate information.
                    Make a comment about the data that answers the user question.
                    Base your answer on the information provided mainly from the HCDP. Provide a summary that answers the question.
                    Use the metric system.
                    """
                )
            )
        else:
            history = "\n".join([f"{msg.role}: {msg.content}" for msg in request.messages])
            response = client.models.generate_content(
                model=model,
                contents=types.Content(
                    role="user", parts=[types.Part(text=history)]
                ),
                config=GenerateContentConfig(
                    tools=[
                        Tool(google_search=GoogleSearch()),
                    ],
                    system_instruction=f"""
                    Today is {today}.
                    You are a Hawaii Data Climate Portal API assistant that helps users with hawaii climate information.
                    Make a comment about the data that answers the user question.
                    Use the metric system.
                    Only include your answer, do not include any other text.
                    """
                )
            )

        if response.candidates and response.candidates[0].content.parts:
            return {"response": response.candidates[0].content.parts[0].text,
                    "extra_params": extra_params}
        else:
            raise HTTPException(
                status_code=500, detail="Failed to get a valid response from the model."
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
