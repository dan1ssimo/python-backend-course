import pytest
import random
from fastapi import HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from httpx import AsyncClient, ASGITransport
from hw3.demo_service.core.users import UserService, UserInfo, UserRole
from hw3.demo_service.api.utils import requires_author, requires_admin


@pytest.mark.anyio
async def test_user_service_initialization(async_client):
    assert hasattr(async_client.state, "user_service")
    user_service: UserService = async_client.state.user_service

    admin_user = user_service.get_by_username("admin")
    assert admin_user is not None
    assert admin_user.info.username == "admin"
    assert admin_user.info.role == UserRole.ADMIN


def test_authorization_valid(test_client, user_service):
    user_service.register(
        UserInfo(
            username="valid_author_user",
            name="Valid Author",
            birthdate="2000-01-01T00:00:00",
            password="validPassword123",
        )
    )

    credentials = HTTPBasicCredentials(
        username="valid_author_user", password="validPassword123"
    )
    user_entity = requires_author(credentials, user_service)

    assert user_entity.info.username == "valid_author_user"


def test_authorization_invalid(test_client, user_service):
    credentials = HTTPBasicCredentials(
        username="invalid_user", password="wrong_password"
    )

    with pytest.raises(HTTPException) as exc_info:
        requires_author(credentials, user_service)

    assert exc_info.value.status_code == 401


def test_admin_authorization_valid(test_client, user_service):
    admin_user = UserInfo(
        username="valid_admin_user",
        name="Valid Admin",
        birthdate="2000-01-01T00:00:00",
        password="validPassword123",
        role=UserRole.ADMIN,
    )
    admin_user = user_service.register(admin_user)

    user_entity = requires_admin(admin_user)
    assert user_entity.info.username == "valid_admin_user"


def test_admin_authorization_invalid(test_client, user_service):
    regular_user = user_service.register(
        UserInfo(
            username="invalid_regular_user",
            name="Invalid Regular",
            birthdate="2000-01-01T00:00:00",
            password="validPassword123",
            role=UserRole.USER,
        )
    )

    with pytest.raises(HTTPException) as exc_info:
        requires_admin(regular_user)

    assert exc_info.value.status_code == 403


def test_user_registration_and_retrieval(test_client, user_service):
    response = test_client.post(
        "/user-register",
        json={
            "username": "new_user",
            "name": "New User",
            "birthdate": "2000-01-01T00:00:00",
            "password": "validPassword123",
        },
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "new_user"

    response = test_client.post(
        "/user-get",
        params={"id": user_data["uid"]},
        headers={"Authorization": "Basic YWRtaW46c3VwZXJTZWNyZXRBZG1pblBhc3N3b3JkMTIz"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == user_data["uid"]
    assert data["username"] == "new_user"
    assert data["name"] == "New User"


@pytest.mark.parametrize(
    "json_data, expected_status, expected_detail",
    [
        (
            {
                "username": "user2",
                "name": "User Two",
                "birthdate": "2000-01-01T00:00:00",
                "password": "short",
            },
            400,
            "invalid password",
        ),
        (
            {
                "username": "user3",
                "birthdate": "2000-01-01T00:00:00",
                "password": "validPassword123",
            },
            422,
            None,
        ),
        (
            {
                "username": "user3",
                "name": "User Three",
                "birthdate": "2000-01-01T00:00:00",
            },
            422,
            None,
        ),
        (
            {
                "username": "user4",
                "name": "User Four",
                "birthdate": "invalid-date",
                "password": "validPassword123",
            },
            422,
            None,
        ),
        (
            {
                "username": "duplicateUser",
                "name": "Duplicate User",
                "birthdate": "2000-01-01T00:00:00",
                "password": "Password12345",
            },
            400,
            "username is already taken",
        ),
    ],
)
def test_invalid_user_registration_scenarios(
    test_client, user_service, json_data, expected_status, expected_detail
):
    if json_data.get("username") == "duplicateUser":
        user_service.register(
            UserInfo(
                username="duplicateUser",
                name="Duplicate User",
                birthdate="2000-01-01T00:00:00",
                password="Password12345",
            )
        )

    response = test_client.post("/user-register", json=json_data)
    assert response.status_code == expected_status
    if expected_detail:
        assert response.json() == {"detail": expected_detail}


@pytest.mark.parametrize(
    "params, expected_status, expected_detail",
    [
        ({}, 400, "neither id nor username are provided"),
        ({"id": 1, "username": "user"}, 400, "both id and username are provided"),
    ],
)
def test_invalid_user_retrieval_scenarios(
    test_client, params, expected_status, expected_detail
):
    response = test_client.post(
        "/user-get",
        params=params,
        headers={"Authorization": "Basic YWRtaW46c3VwZXJTZWNyZXRBZG1pblBhc3N3b3JkMTIz"},
    )
    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}


@pytest.mark.parametrize(
    "params, expected_status",
    [
        ({"id": 132132}, 404),
        ({"username": "unknownUser"}, 404),
    ],
)
def test_user_not_found(test_client, params, expected_status):
    response = test_client.post(
        "/user-get",
        params=params,
        headers={"Authorization": "Basic YWRtaW46c3VwZXJTZWNyZXRBZG1pblBhc3N3b3JkMTIz"},
    )
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "params, headers, expected_status, expected_detail",
    [
        (
            {"id": 132132},
            {"Authorization": "Basic YWRtaW46c3VwZXJTZWNyZXRBZG1pblBhc3N3b3JkMTIz"},
            400,
            "user not found",
        ),
        ({"id": 1}, {"Authorization": "Basic dXNlcjpQYXNzd29yZDEyMw=="}, 401, None),
        ({"id": 1}, {}, 401, None),
    ],
)
def test_invalid_user_promotion_scenarios(
    test_client, params, headers, expected_status, expected_detail
):
    response = test_client.post("/user-promote", params=params, headers=headers)
    assert response.status_code == expected_status
    if expected_detail:
        assert response.json() == {"detail": expected_detail}


@pytest.mark.parametrize(
    "params, expected_status, expected_detail",
    [
        (
            {"id": 1},
            200,
            None,
        ),
    ],
)
def test_valid_user_promotion_scenario(
    test_client, params, expected_status, expected_detail
):
    response = test_client.post(
        "/user-promote",
        params=params,
        headers={"Authorization": "Basic YWRtaW46c3VwZXJTZWNyZXRBZG1pblBhc3N3b3JkMTIz"},
    )
    assert response.status_code == expected_status
    if expected_detail:
        assert response.json() == {"detail": expected_detail}


def test_user_registration_with_admin_role(test_client, user_service):
    response = test_client.post(
        "/user-register",
        json={
            "username": "adminUser",
            "name": "Admin User",
            "birthdate": "2000-01-01T00:00:00",
            "password": "validPassword123",
        },
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "adminUser"

    response = test_client.post(
        "/user-promote",
        params={"id": user_data["uid"]},
        headers={"Authorization": "Basic YWRtaW46c3VwZXJTZWNyZXRBZG1pblBhc3N3b3JkMTIz"},
    )
    assert response.status_code == 200

    response = test_client.post(
        "/user-get",
        params={"id": user_data["uid"]},
        headers={"Authorization": "Basic YWRtaW46c3VwZXJTZWNyZXRBZG1pblBhc3N3b3JkMTIz"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"