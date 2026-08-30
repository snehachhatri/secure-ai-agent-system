from policies import POLICIES


def check_permission(agent_name, action):
    allowed_actions = POLICIES.get(agent_name, [])

    if action in allowed_actions:
        return "ALLOW"

    return "BLOCK"

if __name__ == "__main__":
    print(check_permission("Customer Support Agent", "READ_CUSTOMER"))
    print(check_permission("Customer Support Agent", "DELETE_CUSTOMER"))
    print(check_permission("Customer Support Agent", "CREATE_TICKET"))
    print(check_permission("Malicious Test Agent", "DELETE_CUSTOMER"))