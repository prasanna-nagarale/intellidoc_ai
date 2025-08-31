from ninja import Router

documents_router = Router()
chat_router = Router()
auth_router = Router()

# Example routes
@documents_router.get("/test")
def test_documents(request):
    return {"message": "Documents API working"}

@chat_router.get("/test")
def test_chat(request):
    return {"message": "Chat API working"}

@auth_router.get("/test")
def test_auth(request):
    return {"message": "Auth API working"}
