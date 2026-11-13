def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"

def test_register_login_me(client):
    r = client.post("/api/v1/auth/register", json={
        "name":"Pessoa Teste","email":"teste@example.com","password":"Senha-forte-123!"
    })
    assert r.status_code == 201
    login = client.post("/api/v1/auth/login", data={"username":"teste@example.com","password":"Senha-forte-123!"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization":f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["role"] == "STUDENT"

def test_short_password_rejected(client):
    r = client.post("/api/v1/auth/register", json={"name":"Teste","email":"x@example.com","password":"123"})
    assert r.status_code == 422
