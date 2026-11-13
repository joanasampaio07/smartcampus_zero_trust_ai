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

def test_refresh_rotation_and_logout(client):
    client.post("/api/v1/auth/register", json={"name":"Refresh User","email":"refresh@example.com","password":"Senha-forte-123!"})
    login = client.post("/api/v1/auth/login", data={"username":"refresh@example.com","password":"Senha-forte-123!"})
    assert login.status_code == 200
    rt1 = login.json()["refresh_token"]
    assert rt1
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert refreshed.status_code == 200
    rt2 = refreshed.json()["refresh_token"]
    assert rt2 and rt2 != rt1
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rt1}).status_code == 401
    assert client.post("/api/v1/auth/logout", json={"refresh_token": rt2}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rt2}).status_code == 401

def test_forgot_and_reset_password(client):
    client.post("/api/v1/auth/register", json={"name":"Reset User","email":"reset@example.com","password":"Senha-forte-123!"})
    forgot = client.post("/api/v1/auth/forgot-password", json={"email":"reset@example.com"})
    assert forgot.status_code == 200
    token = forgot.json().get("reset_token")
    assert token
    reset = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Nova-senha-forte-456!"})
    assert reset.status_code == 200
    assert client.post("/api/v1/auth/login", data={"username":"reset@example.com","password":"Nova-senha-forte-456!"}).status_code == 200
