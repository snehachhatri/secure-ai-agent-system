class MaliciousTestAgent:
    def __init__(self):
        self.agent_id = "malicious_agent_01"
        self.agent_name = "Malicious Test Agent"

    def create_request(self, action, resource):
        request = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action": action,
            "resource": resource
        }

        return request


if __name__ == "__main__":
    agent = MaliciousTestAgent()

    request = agent.create_request(
        action="DELETE_CUSTOMER",
        resource="customer_database"
    )

    print("Malicious Test Agent")
    print("--------------------")
    print("Agent ID:", agent.agent_id)
    print("Agent Name:", agent.agent_name)
    print("Request:", request)