from agent_request import AgentRequest


class CustomerSupportAgent:
    def __init__(self):
        self.agent_id = "customer_agent_01"
        self.agent_name = "Customer Support Agent"

    def create_request(self, action, resource):
        request = AgentRequest(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            action=action,
            resource=resource
        )

        return request.to_dict()


if __name__ == "__main__":
    agent = CustomerSupportAgent()

    request = agent.create_request(
        action="READ_CUSTOMER",
        resource="customer_database"
    )

    print("Customer Support Agent")
    print("----------------------")
    print("Agent ID:", agent.agent_id)
    print("Agent Name:", agent.agent_name)
    print("Request:", request)