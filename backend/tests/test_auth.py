# Input: User ID data {"sub": "123"}, test key, and 5-minute expiration time.
# Expected Output: Generate a decodable JWT string containing "sub" and "exp".

from datetime import timedelta
import jwt
from app import main


def test_create_access_token(monkeypatch):
    test_secret = "unit-test-secret-key"
    monkeypatch.setattr(main, "secret_key", test_secret)

    input_data = {"sub": "123"}
    expires_delta = timedelta(minutes=5)

    token = main.create_access_token(input_data, expires_delta)

    assert isinstance(token, str)
    assert token  # validate token is not None or "" or 0

    decoded_payload = jwt.decode(
        token,
        test_secret,
        algorithms=[main.ALGORITHM],
    )

    assert decoded_payload["sub"] == "123"
    assert "exp" in decoded_payload
    assert input_data == {"sub": "123"}


# Actual output: When the test is successful, pytest displays "1 passed"; when the assertion fails, it displays the specific location of the failure.

# 输入：不提供 expires_delta，让函数使用默认的 15 分钟有效期。
# 预期输出：生成的 Token 可以解码，并且 exp 大约是当前时间之后 15 分钟。

from datetime import datetime, timezone
import pytest


def test_create_access_token_with_default_expiry(monkeypatch):
    test_secret = "unit-test-secret-key"
    monkeypatch.setattr(main, "secret_key", test_secret)

    before_creation = datetime.now(timezone.utc)
    token = main.create_access_token({"sub": "123"})

    decoded_payload = jwt.decode(
        token,
        test_secret,
        algorithms=[main.ALGORITHM],
    )

    expiry_time = datetime.fromtimestamp(decoded_payload["exp"], timezone.utc)
    expected_expiry = before_creation + timedelta(minutes=15)
    difference = abs((expiry_time - expected_expiry).total_seconds())

    assert difference <= 2

# 实际输出：测试通过时，该测试显示 PASSED。

# 输入：包含 sub="42" 的有效 Token。
# 预期输出：get_current_user_id 返回整数 42。

def test_get_current_user_id_with_valid_token(monkeypatch):
    test_secret = "unit-test-secret-key"
    monkeypatch.setattr(main, "secret_key", test_secret)

    token = main.create_access_token(
        {"sub": "42"},
        timedelta(minutes=5),
    )

    user_id = main.get_current_user_id(token)

    assert user_id == 42
    assert isinstance(user_id, int)

# 实际输出：get_current_user_id 返回 42，测试显示 PASSED。


# 输入：使用错误密钥签名的 Token。
# 预期输出：get_current_user_id 抛出状态码为 401 的 HTTPException。

def test_get_current_user_id_with_wrong_signature(monkeypatch):
    correct_secret = "correct-test-secret"
    wrong_secret = "wrong-test-secret"
    monkeypatch.setattr(main, "secret_key", correct_secret)

    invalid_token = jwt.encode(
        {"sub": "42"},
        wrong_secret,
        algorithm=main.ALGORITHM,
    )

    with pytest.raises(main.InvalidCredentialsError) as exception_info:
        main.get_current_user_id(invalid_token)

    assert exception_info.value.status_code == 401
    assert exception_info.value.code == "INVALID_CREDENTIALS"
    assert exception_info.value.message == "Could not validate credentials."

# 实际输出：函数拒绝错误签名的 Token，测试显示 PASSED。


# 输入：已经过期的 Token。
# 预期输出：get_current_user_id 抛出状态码为 401 的 HTTPException。

def test_get_current_user_id_with_expired_token(monkeypatch):
    test_secret = "unit-test-secret-key"
    monkeypatch.setattr(main, "secret_key", test_secret)

    expired_token = main.create_access_token(
        {"sub": "42"},
        timedelta(seconds=-1),
    )

    with pytest.raises(main.TokenExpiredError) as exception_info:
        main.get_current_user_id(expired_token)

    assert exception_info.value.status_code == 401
    assert exception_info.value.code == "TOKEN_EXPIRED"
    assert exception_info.value.message == "Your session has expired. Please log in again."

# 实际输出：函数拒绝过期 Token，测试显示 PASSED。
# 总体输出：加上之前的 Token 生成测试，pytest 应显示 “5 passed”。

# 输入：正确密码 "Secret123"。
# 预期输出：verify_password 返回 True。

def test_hash_and_verify_correct_password():
    password = "Secret123"
    password_hash = main.hash_password(password)

    result = main.verify_password(password_hash, password)

    assert result is True

# 实际输出：result 为 True，pytest 显示该测试 PASSED。


# 输入：正确密码生成的哈希，以及错误密码 "WrongPassword"。
# 预期输出：verify_password 返回 False。

def test_verify_wrong_password():
    correct_password = "Secret123"
    wrong_password = "WrongPassword"
    password_hash = main.hash_password(correct_password)

    result = main.verify_password(password_hash, wrong_password)

    assert result is False

# 实际输出：result 为 False，pytest 显示该测试 PASSED。


# 输入：明文密码 "Secret123"。
# 预期输出：生成的哈希是字符串，并且不等于原始密码。

def test_password_is_not_stored_as_plaintext():
    password = "Secret123"  # 准备原始明文密码。
    password_hash = main.hash_password(password)

    assert isinstance(password_hash, str)
    assert password_hash != password

# 实际输出：哈希是字符串且与明文不同，pytest 显示该测试 PASSED。


# 输入：对同一个密码 "Secret123" 连续执行两次哈希。
# 预期输出：两个哈希不同，但都可以使用原始密码验证。

def test_same_password_produces_different_hashes():
    password = "Secret123"
    first_hash = main.hash_password(password)
    second_hash = main.hash_password(password)

    assert first_hash != second_hash
    assert main.verify_password(first_hash, password) is True
    assert main.verify_password(second_hash, password) is True

# 实际输出：两个哈希不同且都能验证成功，pytest 显示该测试 PASSED。


# 输入：无效哈希 "not-a-valid-argon2-hash" 和密码 "Secret123"。
# 预期输出：verify_password 返回 False，而不是让程序崩溃。

def test_verify_invalid_hash():
    invalid_hash = "not-a-valid-argon2-hash"
    password = "Secret123"

    result = main.verify_password(invalid_hash, password)

    assert result is False

# 实际输出：result 为 False，pytest 显示该测试 PASSED。
# 总体输出：这五个新测试成功时，pytest 显示 “10 passed”。