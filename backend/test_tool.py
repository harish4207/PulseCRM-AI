from app.ai.tools import search_hcp

print("Starting...")

result = search_hcp.invoke(
    {
        "doctor_name": "Sharma"
    }
)

print(result)