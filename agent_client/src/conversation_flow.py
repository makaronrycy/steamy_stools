from typing import Dict, Any, Optional, List
import logging

class ConversationFlow:
    """
    Zarządza przepływem rozmowy - AI decyduje o kolejnych pytaniach na podstawie kontekstu.
    Rozumie co użytkownik mówi i wydobywa informacje z dowolnej odpowiedzi.
    """
    
    def __init__(self):
        # WYMAGANE DANE do zebrania
        self.required_data = {
            "identity": {
                "first_name": None,
                "last_name": None,
                "student_index": None,
                "verified": False,
            },
            "self_assessment": {
                "grade": None,
                "description": None,
                "complete": False,
            },
            "teammate_assessments": [],  # [{teammate_index, grade, description}]
            "leadership_assessment": {
                "grade": None,
                "description": None,
                "complete": False,
            },
            "project_assessments": [],  # [{project_id, grade, description}]
            "objectives_assessment": {
                "grade": None,
                "description": None,
                "complete": False,
            },
        }
        
        # KONTEKST rozmowy
        self.context = {
            "project_id": None,
            "project_name": None,
            "is_leader": False,
            "teammates": [],  # Lista kolegów z zespołu
            "all_projects": ["1", "2"],  # Wszystkie projekty do oceny
        }
        
        # HISTORIA rozmowy (ostatnie 10 wiadomości)
        self.conversation_history = []
    
    def determine_next_question(self) -> str:
        """
        Determines the next question prompt to use based on conversation state.
        
        Uses a priority-based decision system to determine which assessment
        should be collected next from the user.
        
        Priority order:
            1. Identity verification (initial_prompt)
            2. Self assessment (self_assessment_prompt)
            3. Teammate assessments (teammate_assessment_*_prompt)
            4. Leadership assessment - only for non-leaders (leadership_assessment_prompt)
            5. Project assessments (project_assessment_prompt)
            6. Objectives assessment (objectives_assessment_prompt)
            7. Completion (completion_check_prompt)
        
        Returns:
            str: The name of the prompt to use for the next question.
        """
        
        # 1. WERYFIKACJA TOŻSAMOŚCI (najważniejsze)
        if not self.required_data["identity"]["verified"]:
            return "initial_prompt"
        
        # 2. SAMOOCENA
        if not self.required_data["self_assessment"]["complete"]:
            return "self_assessment_prompt"
        
        # 3. OCENA KOLEGÓW
        if len(self.required_data["teammate_assessments"]) < len(self.context["teammates"]):
            if len(self.required_data["teammate_assessments"]) == 0:
                return "teammate_assessment_intro_prompt"
            return "teammate_assessment_individual_prompt"
        
        # 4. OCENA LIDERA (tylko jeśli user nie jest liderem)
        if not self.context["is_leader"] and not self.required_data["leadership_assessment"]["complete"]:
            return "leadership_assessment_prompt"
        
        # 5. OCENA PROJEKTÓW
        if len(self.required_data["project_assessments"]) < len(self.context["all_projects"]):
            return "project_assessment_prompt"
        
        # 6. OCENA CELÓW PROJEKTU
        if not self.required_data["objectives_assessment"]["complete"]:
            return "objectives_assessment_prompt"
        
        # 7. WSZYSTKO KOMPLETNE!
        return "completion_check_prompt"
    
    def extract_info_from_response(self, user_response: str, tool_results: List[Dict]) -> Dict[str, Any]:
        """
        Extracts and processes information from user response and tool results.
        
        Parses tool outputs to update internal state (required_data, context)
        based on successful tool calls. Handles various tool types including
        identity verification, grade submissions, and project information.
        
        Args:
            user_response (str): The raw text response from the user.
            tool_results (List[Dict]): List of tool call results, each containing:
                - name (str): Tool name
                - input (dict): Tool input parameters
                - output (str): Tool output/result
        
        Returns:
            Dict[str, Any]: Extracted information with keys like:
                - student_index: Verified student index
                - self_assessment_saved: True if self grade was saved
                - teammate_assessment_saved: Index of graded teammate
                - leadership_assessment_saved: True if leader grade saved
                - project_assessment_saved: ID of graded project
                - objectives_assessment_saved: True if objectives grade saved
        """
        extracted = {}
        
        print(f"=== EXTRACTING INFO ===")
        print(f"User response: {user_response}")
        print(f"Tool results count: {len(tool_results)}")
        print(f"Tool results: {tool_results}")
        
        # Przetwórz wyniki narzędzi
        for tool in tool_results:
            tool_name = tool.get("name", "")
            tool_input = tool.get("input", {})
            tool_output = tool.get("output", "")
            
            print(f"\n--- Processing tool: {tool_name} ---")
            print(f"  Raw input: {tool_input}")
            print(f"  Raw output: {tool_output}")
            
            # check_name_tool
            if "check_name_tool" in tool_name:
                print("  Detected check_name_tool!")
                
                # FIX: Input może być zagnieżdżony w 'param'
                if isinstance(tool_input, dict) and 'param' in tool_input:
                    tool_input = tool_input['param']
                    print(f"  Unwrapped param: {tool_input}")
                
                # ZAPISZ DANE Z INPUT
                if isinstance(tool_input, str):
                    import json
                    try:
                        tool_input = json.loads(tool_input)
                        print(f"  Parsed JSON input: {tool_input}")
                    except:
                        print(f"  Failed to parse JSON input: {tool_input}")
                
                if isinstance(tool_input, dict):
                    fn = tool_input.get("first_name")
                    ln = tool_input.get("last_name")
                    
                    if fn:
                        self.required_data["identity"]["first_name"] = fn
                    if ln:
                        self.required_data["identity"]["last_name"] = ln
                    
                    print(f"  Saved name: {fn} {ln}")
                else:
                    print(f"  tool_input is not dict: {type(tool_input)}")
                
                # PARSUJ OUTPUT JEŚLI JSON
                import json
                output_str = str(tool_output)
                
                # Sprawdź czy to JSON
                if output_str.startswith("{"):
                    try:
                        output_json = json.loads(output_str)
                        # Wyciągnij text z JSON
                        if "text" in output_json:
                            output_str = output_json["text"]
                            print(f"  Extracted text from JSON: {output_str}")
                    except:
                        print(f"  Looks like JSON but failed to parse")
                
                # SPRAWDŹ CZY FOUND
                if "FOUND" in output_str:
                    self.required_data["identity"]["verified"] = True
                    print(f"  FOUND detected!")
                    
                    # REGEX dla indexu
                    import re
                    match = re.search(r'index:\s*(\d+)', output_str)
                    if match:
                        idx = match.group(1)
                        self.required_data["identity"]["student_index"] = idx
                        extracted["student_index"] = idx
                        print(f"  VERIFIED! Index: {idx}")
                    else:
                        # Fallback regex
                        match2 = re.search(r'(\d{4})', output_str)
                        if match2:
                            idx = match2.group(1)
                            self.required_data["identity"]["student_index"] = idx
                            extracted["student_index"] = idx
                            print(f"  VERIFIED! Index (fallback): {idx}")
                        else:
                            print(f"  No index found in: {output_str}")
                else:
                    print(f"  NOT FOUND in output: {output_str}")

            # get_user_info_tool
            elif "get_user_info_tool" in tool_name:
                if "Project:" in tool_output:
                    import re
                    match = re.search(r'Project:\s*(\d+)\s*\(([^)]+)\)', tool_output)
                    if match:
                        self.context["project_id"] = match.group(1)
                        self.context["project_name"] = match.group(2)
            
            # get_ungraded_members_tool
            elif "get_ungraded_members_tool" in tool_name:
                # Parse: "Ungraded teammates: ['2002', '2003']"
                import re
                match = re.search(r'\[(.*?)\]', tool_output)
                if match:
                    teammates_str = match.group(1)
                    # Remove quotes and split
                    teammates = [t.strip().strip("'\"") for t in teammates_str.split(",") if t.strip()]
                    self.context["teammates"] = teammates
            
            # set_self_grade_tool
            elif "set_self_grade_tool" in tool_name and "SUCCESS" in tool_output:
                if isinstance(tool_input, dict):
                    self.required_data["self_assessment"]["grade"] = tool_input.get("grade")
                    self.required_data["self_assessment"]["description"] = tool_input.get("description")
                    self.required_data["self_assessment"]["complete"] = True
                    extracted["self_assessment_saved"] = True
            
            # set_teammate_grade_tool
            elif "set_teammate_grade_tool" in tool_name and "SUCCESS" in tool_output:
                if isinstance(tool_input, dict):
                    self.required_data["teammate_assessments"].append({
                        "teammate_index": tool_input.get("graded_person_index"),
                        "grade": tool_input.get("grade"),
                        "description": tool_input.get("description"),
                    })
                    extracted["teammate_assessment_saved"] = tool_input.get("graded_person_index")
            
            # set_leader_grade_tool
            elif "set_leader_grade_tool" in tool_name and "SUCCESS" in tool_output:
                if isinstance(tool_input, dict):
                    self.required_data["leadership_assessment"]["grade"] = tool_input.get("grade")
                    self.required_data["leadership_assessment"]["description"] = tool_input.get("description")
                    self.required_data["leadership_assessment"]["complete"] = True
                    extracted["leadership_assessment_saved"] = True
            
            # set_project_grade_tool
            elif "set_project_grade_tool" in tool_name and "SUCCESS" in tool_output:
                if isinstance(tool_input, dict):
                    self.required_data["project_assessments"].append({
                        "project_id": tool_input.get("project_id"),
                        "grade": tool_input.get("grade"),
                        "description": tool_input.get("description"),
                    })
                    extracted["project_assessment_saved"] = tool_input.get("project_id")
            
            # set_project_objectives_grade_tool
            elif "set_project_objectives_grade_tool" in tool_name and "SUCCESS" in tool_output:
                if isinstance(tool_input, dict):
                    self.required_data["objectives_assessment"]["grade"] = tool_input.get("grade")
                    self.required_data["objectives_assessment"]["description"] = tool_input.get("description")
                    self.required_data["objectives_assessment"]["complete"] = True
                    extracted["objectives_assessment_saved"] = True
        
        logging.info(f"Extracted from user response + tools: {extracted}")
        return extracted
    
    def add_to_history(self, role: str, message: str):
        """
        Adds a message to the conversation history.
        
        Maintains a rolling window of the last 10 messages to provide
        context for AI agents without overwhelming the context window.
        
        Args:
            role (str): The role of the message sender (e.g., "user", "assistant").
            message (str): The content of the message.
        
        Returns:
            None
        """
        self.conversation_history.append(f"{role}: {message}")
        # Trzymaj tylko ostatnie 10 wiadomości
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]
    
    def get_context_for_prompt(self) -> str:
        """
        Builds a formatted context string for AI prompt injection.
        
        Generates a human-readable summary of the current conversation state,
        including what data has been collected (✓) and what is still missing (✗).
        Also includes the last 3 conversation messages for continuity.
        
        Returns:
            str: Formatted multi-line string containing:
                - Identity information (name, index, verification status)
                - Project context
                - Assessment completion status (self, teammates, leader, projects, objectives)
                - Recent conversation history
        """
        parts = []
        
        # Dane tożsamości
        identity = self.required_data["identity"]
        if identity["first_name"]:
            parts.append(f"✓ Imię: {identity['first_name']}")
        if identity["last_name"]:
            parts.append(f"✓ Nazwisko: {identity['last_name']}")
        if identity["student_index"]:
            parts.append(f"✓ Index: {identity['student_index']}")
        if identity["verified"]:
            parts.append(f"✓ ZWERYFIKOWANY w bazie")
        
        # Projekt
        if self.context["project_name"]:
            parts.append(f"✓ Projekt: {self.context['project_name']} (ID: {self.context['project_id']})")
        
        # Samoocena
        if self.required_data["self_assessment"]["complete"]:
            parts.append(f"✓ Samoocena: {self.required_data['self_assessment']['grade']}")
        else:
            parts.append("✗ Samoocena: BRAK")
        
        # Oceny kolegów
        graded = len(self.required_data["teammate_assessments"])
        total = len(self.context["teammates"])
        if total > 0:
            parts.append(f"✓ Oceny kolegów: {graded}/{total}")
        
        # Ocena lidera
        if self.required_data["leadership_assessment"]["complete"]:
            parts.append(f"✓ Ocena lidera: {self.required_data['leadership_assessment']['grade']}")
        elif not self.context["is_leader"]:
            parts.append("✗ Ocena lidera: BRAK")
        
        # Oceny projektów
        graded_proj = len(self.required_data["project_assessments"])
        total_proj = len(self.context["all_projects"])
        parts.append(f"✓ Oceny projektów: {graded_proj}/{total_proj}")
        
        # Ocena celów
        if self.required_data["objectives_assessment"]["complete"]:
            parts.append(f"✓ Ocena celów: {self.required_data['objectives_assessment']['grade']}")
        else:
            parts.append("✗ Ocena celów: BRAK")
        
        # Historia rozmowy (ostatnie 3)
        if self.conversation_history:
            parts.append("\n=== Ostatnia rozmowa ===")
            for msg in self.conversation_history[-3:]:
                parts.append(msg)
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the conversation flow state to a dictionary.
        
        Used for API responses and state persistence. Converts internal
        state to a flat dictionary structure suitable for JSON serialization.
        
        Returns:
            Dict[str, Any]: Dictionary containing:
                - first_name (str | None): User's first name
                - last_name (str | None): User's last name
                - student_index (str | None): Student index number
                - verified (bool): Whether identity is verified
                - has_self_grade (bool): Whether self assessment is complete
                - graded_teammates (List[str]): List of graded teammate indices
                - graded_projects (List[str]): List of graded project IDs
                - has_leader_grade (bool): Whether leader assessment is complete
                - has_objectives_grade (bool): Whether objectives assessment is complete
                - is_leader (bool): Whether user is a team leader
                - project_id (str | None): User's project ID
                - project_name (str | None): User's project name
        """
        result = {
            "first_name": self.required_data["identity"]["first_name"],
            "last_name": self.required_data["identity"]["last_name"],
            "student_index": self.required_data["identity"]["student_index"],
            "verified": self.required_data["identity"]["verified"],
            "has_self_grade": self.required_data["self_assessment"]["complete"],
            "graded_teammates": [t["teammate_index"] for t in self.required_data["teammate_assessments"]],
            "graded_projects": [p["project_id"] for p in self.required_data["project_assessments"]],
            "has_leader_grade": self.required_data["leadership_assessment"]["complete"],
            "has_objectives_grade": self.required_data["objectives_assessment"]["complete"],
            "is_leader": self.context["is_leader"],
            "project_id": self.context["project_id"],
            "project_name": self.context["project_name"],
        }
        logging.info(f"📋 to_dict() result: {result}")
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        Deserializes a ConversationFlow instance from a dictionary.
        
        Reconstructs the conversation flow state from a previously serialized
        dictionary, typically from API request or database storage.
        
        Args:
            data (Dict[str, Any]): Dictionary containing serialized state with keys:
                - first_name, last_name, student_index, verified
                - has_self_grade, has_leader_grade, has_objectives_grade
                - project_id, project_name, is_leader
        
        Returns:
            ConversationFlow: New instance with restored state.
        """
        flow = cls()
        
        # Załaduj tożsamość
        flow.required_data["identity"]["first_name"] = data.get("first_name")
        flow.required_data["identity"]["last_name"] = data.get("last_name")
        flow.required_data["identity"]["student_index"] = data.get("student_index")
        flow.required_data["identity"]["verified"] = data.get("verified", False)
        
        # Załaduj oceny
        flow.required_data["self_assessment"]["complete"] = data.get("has_self_grade", False)
        flow.required_data["leadership_assessment"]["complete"] = data.get("has_leader_grade", False)
        flow.required_data["objectives_assessment"]["complete"] = data.get("has_objectives_grade", False)
        
        # Załaduj kontekst
        flow.context["project_id"] = data.get("project_id")
        flow.context["project_name"] = data.get("project_name")
        flow.context["is_leader"] = data.get("is_leader", False)
        
        return flow
