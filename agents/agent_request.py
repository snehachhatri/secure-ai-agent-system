class AgentRequest:
    def __init__(self, agent_id, agent_name, action, resource):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.action = action
        self.resource = resource

    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "action": self.action,
            "resource": self.resource
        }