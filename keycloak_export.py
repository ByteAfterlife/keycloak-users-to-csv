import requests
import csv
import getpass

KEYCLOAK_URL = ""
REALM = "master"
USER_REALM = ""
CLIENT_ID = "admin-cli"
ADMIN_USERNAME = ""

def get_admin_token(password, totp=None):
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    data = {
        "grant_type": "password",
        "client_id": CLIENT_ID,
        "username": ADMIN_USERNAME,
        "password": password,
    }
    if totp:
        data["totp"] = totp

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    access_token = response.json()["access_token"]
    return access_token

def get_users(token, first=0, max=1000):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"first": first, "max": max}
    users_url = f"{KEYCLOAK_URL}/admin/realms/{USER_REALM}/users"
    response = requests.get(users_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def main():
    global KEYCLOAK_URL
    global USER_REALM
    global ADMIN_USERNAME
    KEYCLOAK_URL = input("What's your Keycloak base url (example: https://keycloak.example.com) DO NOT INCLUDE A / AT THE END OF IT: ")
    USER_REALM = input("Which realm do you want to get the users from: ").strip()
    ADMIN_USERNAME = input("Enter admin username: ").strip()
    password = getpass.getpass("Admin password: ")
    ONLY_ENABLED = input("Do you want to include disabled user account data in the final file (Y/n): ")
    use_totp = input("Does your Keycloak direct grant flow require totp in authentication (If you don't know, the answer is probably yes, use Y/n): ").lower()
    totp = None
    if use_totp.lower() == "y":
        totp = input("Enter current totp code from your authenticator app: ").strip()
    token = get_admin_token(password, totp)
    users = []
    first = 0
    max_results = 1000

    while True:
        batch = get_users(token, first=first, max=max_results)
        if not batch:
            break
        users.extend(batch)
        first += max_results

    # Find all custom attribute keys (if any)
    attribute_keys = set()
    for user in users:
        if "attributes" in user and user["attributes"]:
            attribute_keys.update(user["attributes"].keys())

    # Prepare CSV headers
    base_headers = ["email", "username", "firstName", "lastName", "enabled"]
    headers = base_headers + sorted(attribute_keys)

    # Prepare rows
    rows = []
    for user in users:
        if ONLY_ENABLED.lower() == "y" and not user.get("enabled"):
            continue
        row = [
            user.get("email", ""),
            user.get("username", ""),
            user.get("firstName", ""),
            user.get("lastName", ""),
            user.get("enabled", "")
        ]
        # Add custom attributes
        for key in sorted(attribute_keys):
            value = user.get("attributes", {}).get(key, "")
            # Keycloak attributes can be lists
            if isinstance(value, list):
                value = ";".join(value)
            row.append(value)
        rows.append(row)

    with open("keycloak_users_full.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)

if __name__ == "__main__":
    main()
    print("Task completed! We've put the data into ./keycloak_users_full.csv")
