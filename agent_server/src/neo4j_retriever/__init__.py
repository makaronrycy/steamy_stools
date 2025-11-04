from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

#to solve problems with .env path
from pathlib import Path

print(Path(__file__).parent.parent.parent / '.env')
load_dotenv(Path(__file__).parent.parent.parent/ '.env') #path set for .env in the root directory

class Neo4jRetriever:
    def __init__(self, uri=None, username=None, password=None):
        self.driver = GraphDatabase.driver(
            uri or os.getenv("NEO4J_URI"),
            auth=(username or os.getenv("NEO4J_USERNAME"), 
                  password or os.getenv("NEO4J_PASSWORD"))
        )


#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------GET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def get_node_types(self):
        return {"node_types": []}
    
    def get_students(self):
        with self.driver.session() as session:
            result = session.run("MATCH (s:Student) RETURN s.name AS name, s.surname AS surname, s.index AS index")
            return [{"name": record["name"], "surname": record["surname"], "index": record["index"]} for record in result]
    def get_leader_of_student(self, index: str):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (leader:Student)-[r:belongs_to]->(project)
                WHERE r.role = "leader"
                RETURN leader.name AS name, leader.surname AS surname, leader.index AS index
            """, index=index)
            record = result.single()
            if record:
                return {"name": record["name"], "surname": record["surname"], "index": record["index"]}
            return None
    def get_project_grades(self, project_id: str):
        """
        Get project grades (id) [all grades with information whether the person was in the project] 
        -> grade, justification, grader_index, was_member
        
        Args:
            project_id: Project ID
            
        Returns:
            List of project grades with information about grader's membership
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project {id: $project_id})
                OPTIONAL MATCH (grader:Student)-[:answered]->(answer:Answer)-[:refers_to]->(project)
                WHERE answer.question_type = "project_assessment"
                OPTIONAL MATCH (grader)-[belongs:belongs_to]->(project)
                RETURN answer.grade as grade,
                       answer.explanation as explanation,
                       grader.index as grader_index,
                       CASE WHEN belongs IS NOT NULL THEN true ELSE false END as was_member
                ORDER BY grader.index
            """, project_id=project_id)
            
            return [{"grade": record["grade"], 
                    "explanation": record["explanation"], 
                    "grader_index": record["grader_index"],
                    "was_member": record["was_member"]} for record in result]

    def get_member_grades(self, index: str):
        """
        Get grades for a given member (index) [mark leader grades] 
        -> grade, justification, grader_index, is_leader
        
        Args:
            index: Index of the graded member
            
        Returns:
            List of member grades with information if grader was a leader
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (graded:Student {index: $index})
                OPTIONAL MATCH (grader:Student)-[:answered]->(answer:Answer)-[:refers_to]->(graded)
                WHERE answer.question_type = "teammate_assessment"
                OPTIONAL MATCH (grader)-[r:belongs_to]->(project:Project)
                OPTIONAL MATCH (graded)-[:belongs_to]->(same_project:Project)
                WHERE project = same_project AND r.role = "leader"
                RETURN answer.grade as grade,
                       answer.explanation as explanation,
                       grader.index as grader_index,
                       CASE WHEN r.role = "leader" THEN true ELSE false END as is_leader
                ORDER BY grader.index
            """, index=index)
            
            return [{"grade": record["grade"], 
                    "explanation": record["explanation"], 
                    "grader_index": record["grader_index"],
                    "is_leader": record["is_leader"]} for record in result]

    def is_leader(self, index: str):
        """
        Check if student is a leader
        
        Args:
            index: Student index
            
        Returns:
            bool: True if student is a leader
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $index})-[r:belongs_to]->(project:Project)
                WHERE r.role = "leader"
                RETURN COUNT(r) > 0 as is_leader
            """, index=index)
            
            record = result.single()
            return record["is_leader"] if record else False

    def get_project_members(self, project_id: str):
        """
        Get all member indexes from a given project
        
        Args:
            project_id: Project ID
            
        Returns:
            List of project member indexes
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student)-[:belongs_to]->(project:Project {id: $project_id})
                RETURN student.index as index
                ORDER BY student.index
            """, project_id=project_id)
            
            return [record["index"] for record in result]

    def get_user_info(self, index: str):
        """
        Get user information
        
        Args:
            index: Student index
            
        Returns:
            Dictionary with user information
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $index})
                OPTIONAL MATCH (student)-[:belongs_to]->(project:Project)
                RETURN student.name as name,
                       student.surname as surname,
                       student.github as github,
                       project.id as project_id,
                       project.name as project_name
            """, index=index)
            
            record = result.single()
            if record:
                return {
                    "name": record["name"],
                    "surname": record["surname"], 
                    "github": record["github"],
                    "project_id": record["project_id"],
                    "project_name": record["project_name"]
                }
            return None

    def has_graded_all_members(self, index: str):
        """
        Check if user has graded all team members
        
        Args:
            index: Grader index
            
        Returns:
            bool: True if graded all team members
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.index <> $index
                WITH grader, collect(teammate.index) as all_teammates
                OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(graded:Student)
                WHERE answer.question_type = "teammate_assessment"
                WITH all_teammates, collect(graded.index) as graded_teammates
                RETURN size(all_teammates) = size(graded_teammates) AND size(all_teammates) > 0 as has_graded_all
            """, index=index)
            
            record = result.single()
            return record["has_graded_all"] if record else False

    def get_ungraded_members(self, index: str):
        """
        Get list of ungraded team members
        
        Args:
            index: Grader index
            
        Returns:
            List of indexes of ungraded members
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.index <> $index
                WITH grader, teammate
                OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(teammate)
                WHERE answer.question_type = "teammate_assessment"
                WITH teammate, answer
                WHERE answer IS NULL
                RETURN 
                    teammate.index as ungraded_index,
                    teammate.name as name,
                    teammate.surname as surname
                ORDER BY teammate.index
            """, index=index)
            
            return [{"index": record["ungraded_index"], "name": record["name"], "surname": record["surname"]} for record in result]
    def get_random_ungraded_member(self, index: str):
        """
        Get a random ungraded team member
        
        Args:
            index: Grader index
            
        Returns:
            Dictionary with index, name, surname of a random ungraded member or None
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.index <> $index
                WITH grader, teammate
                OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(teammate)
                WHERE answer.question_type = "teammate_assessment"
                WITH teammate, answer
                WHERE answer IS NULL
                RETURN 
                    teammate.index as ungraded_index,
                    teammate.name as name,
                    teammate.surname as surname
                ORDER BY rand()
                LIMIT 1
            """, index=index)
            
            record = result.single()
            if record:
                return {
                    "index": record["ungraded_index"],
                    "name": record["name"],
                    "surname": record["surname"]
                }
            return None
    def has_graded_all_projects(self, index: str):
        """
        Check if user has graded all projects
        
        Args:
            index: Grader index
            
        Returns:
            bool: True if graded all projects
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project)
                WITH collect(project.id) as all_projects
                MATCH (grader:Student {index: $index})
                OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(graded_project:Project)
                WHERE answer.question_type = "project_assessment"
                WITH all_projects, collect(graded_project.id) as graded_projects
                RETURN size(all_projects) = size(graded_projects) AND size(all_projects) > 0 as has_graded_all
            """, index=index)
            
            record = result.single()
            return record["has_graded_all"] if record else False

    def get_ungraded_projects(self, index: str):
        """
        Get list of ungraded projects
        
        Args:
            index: Grader index
            
        Returns:
            List of ungraded project IDs
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project)
                WITH project
                MATCH (grader:Student {index: $index})
                OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(project)
                WHERE answer.question_type = "project_assessment"
                WITH project, answer
                WHERE answer IS NULL
                RETURN project.id as ungraded_project_id
                ORDER BY project.id
            """, index=index)
            
            return [record["ungraded_project_id"] for record in result]

    def get_student_completion_status(self, index: str):
        """
        Check completion status of all answer types for a given student
        
        Args:
            index: Student index
            
        Returns:
            dict: {
                "all_complete": bool,
                "self_assessment": {
                    "has_grade": bool,
                    "has_explanation": bool,
                    "is_complete": bool
                },
                "teammate_assessments": {
                    "total_required": int,
                    "completed": int,
                    "is_complete": bool,
                    "incomplete_details": [
                        {
                            "teammate_index": str,
                            "has_grade": bool,
                            "has_explanation": bool
                        }
                    ]
                },
                "project_assessments": {
                    "total_required": int,
                    "completed": int,
                    "is_complete": bool,
                    "incomplete_details": [
                        {
                            "project_id": str,
                            "has_grade": bool,
                            "has_explanation": bool
                        }
                    ]
                },
                "leadership_assessment": {
                    "required": bool,
                    "has_grade": bool,
                    "has_explanation": bool,
                    "is_complete": bool,
                    "leader_index": str or None
                },
                "objectives_assessment": {
                    "has_grade": bool,
                    "has_explanation": bool,
                    "is_complete": bool,
                    "project_id": str or None
                }
            }
        """
        with self.driver.session() as session:
            result = {}
            
            # 1. SELF ASSESSMENT
            self_result = session.run("""
                MATCH (student:Student {index: $index})
                OPTIONAL MATCH (student)-[:answered]->(answer:Answer)-[:refers_to]->(student)
                WHERE answer.question_type = "self_assessment"
                RETURN answer.grade as grade, 
                       answer.explanation as explanation
            """, index=index)
            
            self_record = self_result.single()
            if self_record:
                has_grade = self_record["grade"] is not None
                has_explanation = self_record["explanation"] is not None and str(self_record["explanation"]).strip() != ""
            else:
                has_grade = False
                has_explanation = False
                
            result["self_assessment"] = {
                "has_grade": has_grade,
                "has_explanation": has_explanation,
                "is_complete": has_grade and has_explanation
            }
            
            # 2. TEAMMATE ASSESSMENTS
            teammates_result = session.run("""
                MATCH (grader:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.index <> $index
                RETURN teammate.index as teammate_index
                ORDER BY teammate.index
            """, index=index)
            
            all_teammates = [record["teammate_index"] for record in teammates_result]
            total_teammates = len(all_teammates)
            
            incomplete_teammates = []
            completed_teammates = 0
            
            for teammate_idx in all_teammates:
                teammate_answer = session.run("""
                    MATCH (grader:Student {index: $grader_index})
                    MATCH (teammate:Student {index: $teammate_index})
                    OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(teammate)
                    WHERE answer.question_type = "teammate_assessment"
                    RETURN answer.grade as grade,
                           answer.explanation as explanation
                """, grader_index=index, teammate_index=teammate_idx).single()
                
                if teammate_answer:
                    has_grade = teammate_answer["grade"] is not None
                    has_explanation = teammate_answer["explanation"] is not None and str(teammate_answer["explanation"]).strip() != ""
                else:
                    has_grade = False
                    has_explanation = False
                
                if has_grade and has_explanation:
                    completed_teammates += 1
                else:
                    incomplete_teammates.append({
                        "teammate_index": teammate_idx,
                        "has_grade": has_grade,
                        "has_explanation": has_explanation
                    })
            
            result["teammate_assessments"] = {
                "total_required": total_teammates,
                "completed": completed_teammates,
                "is_complete": completed_teammates == total_teammates,
                "incomplete_details": incomplete_teammates
            }
            
            # 3. PROJECT ASSESSMENTS
            projects_result = session.run("""
                MATCH (project:Project)
                RETURN project.id as project_id
                ORDER BY project.id
            """)
            
            all_projects = [record["project_id"] for record in projects_result]
            total_projects = len(all_projects)
            
            incomplete_projects = []
            completed_projects = 0
            
            for proj_id in all_projects:
                project_answer = session.run("""
                    MATCH (grader:Student {index: $index})
                    MATCH (project:Project {id: $project_id})
                    OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(project)
                    WHERE answer.question_type = "project_assessment"
                    RETURN answer.grade as grade,
                           answer.explanation as explanation
                """, index=index, project_id=proj_id).single()
                
                if project_answer:
                    has_grade = project_answer["grade"] is not None
                    has_explanation = project_answer["explanation"] is not None and str(project_answer["explanation"]).strip() != ""
                else:
                    has_grade = False
                    has_explanation = False
                
                if has_grade and has_explanation:
                    completed_projects += 1
                else:
                    incomplete_projects.append({
                        "project_id": proj_id,
                        "has_grade": has_grade,
                        "has_explanation": has_explanation
                    })
            
            result["project_assessments"] = {
                "total_required": total_projects,
                "completed": completed_projects,
                "is_complete": completed_projects == total_projects,
                "incomplete_details": incomplete_projects
            }
            
            # 4. LEADERSHIP ASSESSMENT
            leadership_result = session.run("""
                MATCH (grader:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (leader:Student)-[r:belongs_to]->(project)
                WHERE r.role = "leader"
                RETURN leader.index as leader_index
            """, index=index)
            
            leadership_record = leadership_result.single()
            
            if leadership_record:
                leader_idx = leadership_record["leader_index"]
                leadership_answer = session.run("""
                    MATCH (grader:Student {index: $index})
                    MATCH (leader:Student {index: $leader_index})
                    OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(leader)
                    WHERE answer.question_type = "leadership_assessment"
                    RETURN answer.grade as grade,
                           answer.explanation as explanation
                """, index=index, leader_index=leader_idx).single()
                
                if leadership_answer:
                    has_grade = leadership_answer["grade"] is not None
                    has_explanation = leadership_answer["explanation"] is not None and str(leadership_answer["explanation"]).strip() != ""
                else:
                    has_grade = False
                    has_explanation = False
                
                result["leadership_assessment"] = {
                    "required": True,
                    "has_grade": has_grade,
                    "has_explanation": has_explanation,
                    "is_complete": has_grade and has_explanation,
                    "leader_index": leader_idx
                }
            else:
                result["leadership_assessment"] = {
                    "required": False,
                    "has_grade": False,
                    "has_explanation": False,
                    "is_complete": True,
                    "leader_index": None
                }
            
            # 5. OBJECTIVES ASSESSMENT
            objectives_result = session.run("""
                MATCH (student:Student {index: $index})-[:belongs_to]->(project:Project)
                OPTIONAL MATCH (student)-[:answered]->(answer:Answer)-[:refers_to]->(project)
                WHERE answer.question_type = "objectives_assessment"
                RETURN project.id as project_id,
                       answer.grade as grade,
                       answer.explanation as explanation
            """, index=index)
            
            objectives_record = objectives_result.single()
            
            if objectives_record:
                proj_id = objectives_record["project_id"]
                has_grade = objectives_record["grade"] is not None
                has_explanation = objectives_record["explanation"] is not None and str(objectives_record["explanation"]).strip() != ""
            else:
                proj_id = None
                has_grade = False
                has_explanation = False
            
            result["objectives_assessment"] = {
                "has_grade": has_grade,
                "has_explanation": has_explanation,
                "is_complete": has_grade and has_explanation,
                "project_id": proj_id
            }
            
            result["all_complete"] = (
                result["self_assessment"]["is_complete"] and
                result["teammate_assessments"]["is_complete"] and
                result["project_assessments"]["is_complete"] and
                result["leadership_assessment"]["is_complete"] and
                result["objectives_assessment"]["is_complete"]
            )
            
            return result

    def identify_teammate_by_name(self, grader_index: str, name: str,surname: str|None):
        """
        Identify teammates by name from the same project
        
        Args:
            grader_index: Index of the student searching
            name: Name to search for
            
        Returns:
            List of dicts: [{"name": str, "surname": str, "index": str}]
        """
        where_statement = "AND toLower(teammate.name) = toLower($name)"
        if surname is not None:
            where_statement += " AND toLower(teammate.surname) = toLower($surname)"
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $grader_index})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.index <> $grader_index 
                    """ + where_statement + """
                        RETURN teammate.name AS name, 
                       teammate.surname AS surname, 
                       teammate.index AS index
                ORDER BY teammate.surname, teammate.name
            """, grader_index=grader_index, name=name,surname=surname)
            
            return [{"name": record["name"], 
                    "surname": record["surname"], 
                    "index": record["index"]} for record in result]

    def identify_teammate_by_surname(self, grader_index: str, surname: str):
        """
        Identify teammates by surname from the same project

        Args:
            grader_index: Index of the student searching
            surname: Surname to search for

        Returns:
            List of dicts: [{"name": str, "surname": str, "index": str}]
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $grader_index})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.index <> $grader_index
                  AND toLower(teammate.surname) = toLower($surname)
                RETURN teammate.name AS name,
                       teammate.surname AS surname,
                       teammate.index AS index
                ORDER BY teammate.surname, teammate.name
            """, grader_index=grader_index, surname=surname)

            return [{"name": record["name"],
                    "surname": record["surname"],
                    "index": record["index"]} for record in result]

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------CONVERSATION SESSION METHODS----------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_or_create_session(self, student_index: str):
        """
        Get active conversation session for a student, or create new one if none exists

        Args:
            student_index: Student index

        Returns:
            dict: {
                "session_id": str,
                "student_index": str,
                "current_state": str,
                "started_at": datetime,
                "last_updated": datetime,
                "is_active": bool
            }
        """
        session = self.get_active_session(student_index)
        if session:
            return session
        return self.create_conversation_session(student_index)

    def create_conversation_session(self, student_index: str):
        """
        Create new conversation session for a student

        Args:
            student_index: Student index

        Returns:
            dict: Session information
        """
        import uuid

        session_id = str(uuid.uuid4())

        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})
                CREATE (cs:ConversationSession {
                    session_id: $session_id,
                    student_index: $student_index,
                    current_state: "initial",
                    last_state: null,
                    started_at: datetime(),
                    last_updated: datetime(),
                    is_active: true,
                    completed: false
                })
                CREATE (student)-[:HAS_SESSION]->(cs)
                RETURN cs.session_id as session_id,
                       cs.student_index as student_index,
                       cs.current_state as current_state,
                       cs.last_state as last_state,
                       cs.started_at as started_at,
                       cs.last_updated as last_updated,
                       cs.is_active as is_active,
                       cs.completed as completed
            """, session_id=session_id, student_index=student_index)

            record = result.single()
            if record:
                return {
                    "session_id": record["session_id"],
                    "student_index": record["student_index"],
                    "current_state": record["current_state"],
                    "last_state": record["last_state"],
                    "started_at": record["started_at"],
                    "last_updated": record["last_updated"],
                    "is_active": record["is_active"],
                    "completed": record["completed"]
                }
            return None

    def get_active_session(self, student_index: str):
        """
        Get active conversation session for a student

        Args:
            student_index: Student index

        Returns:
            dict or None: Session information if active session exists
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})-[:HAS_SESSION]->(cs:ConversationSession)
                WHERE cs.is_active = true AND cs.completed = false
                RETURN cs.session_id as session_id,
                       cs.student_index as student_index,
                       cs.current_state as current_state,
                       cs.last_state as last_state,
                       cs.started_at as started_at,
                       cs.last_updated as last_updated,
                       cs.is_active as is_active,
                       cs.completed as completed
                ORDER BY cs.last_updated DESC
                LIMIT 1
            """, student_index=student_index)

            record = result.single()
            if record:
                return {
                    "session_id": record["session_id"],
                    "student_index": record["student_index"],
                    "current_state": record["current_state"],
                    "last_state": record["last_state"],
                    "started_at": record["started_at"],
                    "last_updated": record["last_updated"],
                    "is_active": record["is_active"],
                    "completed": record["completed"]
                }
            return None

    def update_session_state(self, session_id: str, new_state: str, previous_state = None):
        """
        Update current state of conversation session

        Args:
            session_id: Session ID
            new_state: New state name
            previous_state: Optional - the state we're transitioning from (becomes last_state)

        Returns:
            bool: True if update successful
        """
        with self.driver.session() as session:
            if previous_state is not None:
                result = session.run("""
                    MATCH (cs:ConversationSession {session_id: $session_id})
                    SET cs.last_state = cs.current_state,
                        cs.current_state = $new_state,
                        cs.last_updated = datetime()
                    RETURN cs.session_id as session_id
                """, session_id=session_id, new_state=new_state)
            else:
                result = session.run("""
                    MATCH (cs:ConversationSession {session_id: $session_id})
                    SET cs.current_state = $new_state,
                        cs.last_updated = datetime()
                    RETURN cs.session_id as session_id
                """, session_id=session_id, new_state=new_state)

            return result.single() is not None

    def save_conversation_message(self, session_id: str, role: str, content: str, state_at_time: str):
        """
        Save a conversation message to the session

        Args:
            session_id: Session ID
            role: Message role ("user" or "assistant")
            content: Message content
            state_at_time: State when message was sent

        Returns:
            dict: Saved message information
        """
        import uuid

        message_id = str(uuid.uuid4())

        with self.driver.session() as session:
            result = session.run("""
                MATCH (cs:ConversationSession {session_id: $session_id})
                CREATE (cm:ConversationMessage {
                    message_id: $message_id,
                    role: $role,
                    content: $content,
                    state_at_time: $state_at_time,
                    timestamp: datetime()
                })
                CREATE (cs)-[r:HAS_MESSAGE]->(cm)
                WITH cs, cm, r
                MATCH (cs)-[rel:HAS_MESSAGE]->(m:ConversationMessage)
                WITH cm, count(rel) as sequence
                RETURN cm.message_id as message_id,
                       cm.role as role,
                       cm.content as content,
                       cm.state_at_time as state_at_time,
                       cm.timestamp as timestamp,
                       sequence
            """, session_id=session_id, message_id=message_id, role=role,
                 content=content, state_at_time=state_at_time)

            record = result.single()
            if record:
                return {
                    "message_id": record["message_id"],
                    "role": record["role"],
                    "content": record["content"],
                    "state_at_time": record["state_at_time"],
                    "timestamp": record["timestamp"],
                    "sequence": record["sequence"]
                }
            return None

    def get_conversation_history(self, session_id: str, limit = None):
        """
        Get conversation history for a session

        Args:
            session_id: Session ID
            limit: Optional limit on number of messages to return (most recent)

        Returns:
            list: List of messages in chronological order
        """
        with self.driver.session() as session:
            query = """
                MATCH (cs:ConversationSession {session_id: $session_id})-[:HAS_MESSAGE]->(cm:ConversationMessage)
                RETURN cm.message_id as message_id,
                       cm.role as role,
                       cm.content as content,
                       cm.state_at_time as state_at_time,
                       cm.timestamp as timestamp
                ORDER BY cm.timestamp ASC
            """

            if limit is not None:
                query += " LIMIT $limit"
                result = session.run(query, session_id=session_id, limit=limit)
            else:
                result = session.run(query, session_id=session_id)

            return [{
                "role": record["role"],
                "content": record["content"],
                "state_at_time": record["state_at_time"],
            } for record in result]

    def mark_session_complete(self, session_id: str):
        """
        Mark conversation session as completed

        Args:
            session_id: Session ID

        Returns:
            bool: True if update successful
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (cs:ConversationSession {session_id: $session_id})
                SET cs.completed = true,
                    cs.is_active = false,
                    cs.last_updated = datetime()
                RETURN cs.session_id as session_id
            """, session_id=session_id)

            return result.single() is not None

    def get_next_required_state(self, student_index: str):
        """
        Determine the next required state based on completion status

        Args:
            student_index: Student index

        Returns:
            dict: {
                "state": str (state name),
                "reason": str (why this state is next),
                "details": dict (additional context)
            }
        """
        status = self.get_student_completion_status(student_index)

        # Priority 1: Self evaluation
        if not status["self_assessment"]["is_complete"]:
            missing = []
            if not status["self_assessment"]["has_grade"]:
                missing.append("grade")
            if not status["self_assessment"]["has_explanation"]:
                missing.append("explanation")

            return {
                "next_state": "self_evaluation",
                "reason": "self_assessment_incomplete",
                "details": {
                    "missing_fields": missing
                }
            }

        # Priority 2: Teammate assessments
        if not status["teammate_assessments"]["is_complete"]:
            incomplete = status["teammate_assessments"]["incomplete_details"]
            return {
                "next_state": "evaluate_teammate_grade",
                "reason": "teammate_assessments_incomplete",
                "details": {
                    "total_required": status["teammate_assessments"]["total_required"],
                    "completed": status["teammate_assessments"]["completed"],
                    "remaining": len(incomplete),
                    "next_teammate": incomplete[0] if incomplete else None
                }
            }

        # Priority 3: Project assessments
        if not status["project_assessments"]["is_complete"]:
            incomplete = status["project_assessments"]["incomplete_details"]
            return {
                "next_state": "evaluate_project_grade",
                "reason": "project_assessments_incomplete",
                "details": {
                    "total_required": status["project_assessments"]["total_required"],
                    "completed": status["project_assessments"]["completed"],
                    "remaining": len(incomplete),
                    "next_project": incomplete[0] if incomplete else None
                }
            }

        # Priority 4: Leadership assessment (if required and user is not the leader)
        if status["leadership_assessment"]["required"] and not status["leadership_assessment"]["is_complete"]:
            is_user_leader = self.is_leader(student_index)
            if not is_user_leader:  # Only non-leaders evaluate leadership
                return {
                    "next_state": "evaluate_leadership",
                    "reason": "leadership_assessment_incomplete",
                    "details": {
                        "leader_index": status["leadership_assessment"]["leader_index"]
                    }
                }

        # Priority 5: Objectives assessment
        if not status["objectives_assessment"]["is_complete"]:
            return {
                "next_state": "evaluate_objectives",
                "reason": "objectives_assessment_incomplete",
                "details": {
                    "project_id": status["objectives_assessment"]["project_id"]
                }
            }

        # All complete
        return {
            "next_state": "done",
            "reason": "all_assessments_complete",
            "details": {
                "completion_summary": status
            }
        }

    def close(self):
        self.driver.close()

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------SET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def set_self_grade(
        self, 
        grading_person_index: str,
        grade: float,
        description: str,
    ):
        """
        Save student self-assessment
        
        Args:
            grading_person_index: Index number of the person grading themselves
            grade: Grade (e.g. 2-5)
            description: Grade justification
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $grading_person_index})
                CREATE (student)-[:answered]->(o:Answer {
                    question_type: "self_assessment",
                    grade: $grade,
                    explanation: $description
                })-[:refers_to]->(student)
                RETURN student.name as name, 
                    student.surname as surname,
                    student.index as index,
                    o.question_type,
                    o.grade, 
                    o.explanation
            """,
                grading_person_index=grading_person_index,
                grade=grade,
                description=description
            )
            return result.single()

    def set_teammate_grade(
        self, 
        grading_person_index: str,
        graded_person_index: str,
        grade: float,
        description: str,
    ):
        """
        Save team member assessment
        
        Args:
            grading_person_index: Index number of the person grading
            graded_person_index: Index number of the person being graded
            grade: Grade (e.g. 2-5)
            description: Grade justification
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (autor:Student {index: $grading_person_index}),
                    (oceniany:Student {index: $graded_person_index})
                CREATE (autor)-[:answered]->(o:Answer {
                    question_type: "teammate_assessment",
                    grade: $grade,
                    explanation: $description
                })-[:refers_to]->(oceniany)
                RETURN autor.name as grader_name, 
                    autor.surname as grader_surname,
                    oceniany.name as graded_name,
                    oceniany.surname as graded_surname,
                    o.grade, 
                    o.explanation
            """,
                grading_person_index=grading_person_index,
                graded_person_index=graded_person_index,
                grade=grade,
                description=description
            )
            return result.single()
    
    def set_leader_grade(
        self, 
        grading_person_index: str,
        project_id: str,
        grade: float,
        description: str,
    ):
        """
        Save project leader assessment
        
        Args:
            grading_person_index: Index number of the person grading
            project_id: ID of the project whose leader is being assessed
            grade: Grade for leadership (e.g. 2-5)
            description: Justification for the grade
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $grading_person_index})
                MATCH (leader:Student)-[r:belongs_to]->(project:Project {id: $project_id})
                WHERE r.role = "leader"
                CREATE (grader)-[:answered]->(a:Answer {
                    question_type: "leadership_assessment",
                    grade: $grade,
                    explanation: $description
                })-[:refers_to]->(leader)
                RETURN grader.name as grader_name,
                    grader.surname as grader_surname,
                    leader.name as leader_name,
                    leader.surname as leader_surname,
                    leader.index as leader_index,
                    project.id as project_id,
                    project.name as project_name,
                    a.grade,
                    a.explanation
            """,
                grading_person_index=grading_person_index,
                project_id=project_id,
                grade=grade,
                description=description
            )
            return result.single()

    def set_project_grade(
        self, 
        grading_person_index: str,
        project_id: str,
        grade: float,
        description: str,
    ):
        """
        Save project assessment
        
        Args:
            grading_person_index: Index number of the person grading
            project_id: ID of the project
            grade: Grade for the project (e.g. 2-5)
            description: Justification for the grade
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $grading_person_index})
                MATCH (project:Project {id: $project_id})
                CREATE (student)-[:answered]->(a:Answer {
                    question_type: "project_assessment",
                    grade: $grade,
                    explanation: $description
                })-[:refers_to]->(project)
                RETURN student.name as grader_name,
                    student.surname as grader_surname,
                    student.index as grader_index,
                    project.id as project_id,
                    project.name as project_name,
                    a.question_type,
                    a.grade,
                    a.explanation
            """,
                grading_person_index=grading_person_index,
                project_id=project_id,
                grade=grade,
                description=description
            )
            return result.single()

    def set_project_objectives_grade(
        self, 
        grading_person_index: str,
        project_id: str,
        grade: float,
        description: str,
    ):
        """
        Save project objectives assessment
        
        Args:
            grading_person_index: Index number of the person grading
            project_id: ID of the project
            grade: Grade for project objectives (e.g. 2-5)
            description: Justification for the grade
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $grading_person_index})
                MATCH (project:Project {id: $project_id})
                CREATE (student)-[:answered]->(a:Answer {
                    question_type: "objectives_assessment",
                    grade: $grade,
                    explanation: $description
                })-[:refers_to]->(project)
                RETURN student.name as grader_name,
                    student.surname as grader_surname,
                    student.index as grader_index,
                    project.id as project_id,
                    project.name as project_name,
                    a.question_type,
                    a.grade,
                    a.explanation
            """,
                grading_person_index=grading_person_index,
                project_id=project_id,
                grade=grade,
                description=description
            )
            return result.single()

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------FILL DATABASE-------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def fill_database_with_grades(self, csv_path: str):
        """
        Load all grades from CSV file and add them to Neo4j database.

        Args:
            csv_path (str): Path to CSV file containing columns:
                type, grader_id, project_id, graded_id, grade, explanation
        """
        import csv

        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            count = 0


            for row in csv_reader:
                # Skip rows with comments or empty rows
                if not row.get('type') or row['type'].strip().startswith('#'):
                    continue
                
                # Skip rows with missing required data
                if not row.get('grader_id') or not row.get('grade'):
                    print(f"Skipping row with missing data: {row}")
                    continue
                
                try:
                    grade_type = row['type'].strip()
                    grader_id = row['grader_id']
                    project_id = row['project_id'] if row.get('project_id') and row['project_id'].strip() else None
                    graded_id = row['graded_id'] if row.get('graded_id') and row['graded_id'].strip() else None
                    grade = float(row['grade'])
                    explanation = row.get('explanation', '').strip()
                except (ValueError, TypeError) as e:
                    print(f"Data conversion error in row: {row}. Error: {e}")
                    continue

                try:
                    if grade_type == "self_assessment":
                        self.set_self_grade(
                            grading_person_index=grader_id,
                            grade=grade,
                            description=explanation
                        )

                    elif grade_type == "teammate_assessment" and graded_id:
                        self.set_teammate_grade(
                            grading_person_index=grader_id,
                            graded_person_index=graded_id,
                            grade=grade,
                            description=explanation
                        )

                    elif grade_type == "leadership_assessment":
                        self.set_leader_grade(
                            grading_person_index=grader_id,
                            project_id=project_id,
                            grade=grade,
                            description=explanation
                        )

                    elif grade_type == "project_assessment":
                        self.set_project_grade(
                            grading_person_index=grader_id,
                            project_id=project_id,
                            grade=grade,
                            description=explanation
                        )

                    elif grade_type == "objectives_assessment":
                        self.set_project_objectives_grade(
                            grading_person_index=grader_id,
                            project_id=project_id,
                            grade=grade,
                            description=explanation
                        )

                    count += 1
                    print(f"[{count}] Saved grade type '{grade_type}' from {grader_id}")

                except Exception as e:
                    print(f"Error saving grade type '{grade_type}' from {grader_id}: {e}")

        print(f"Completed! Loaded {count} grades from file '{csv_path}'")

    def fill_database_no_grades(self, csv_path: str):
        """
        Fill database with students and projects from CSV file
        
        Args:
            csv_path: Path to CSV file
        
        Format CSV:
            index,name,surname,github,project_id,project_name,role
        """
        import csv
        
        with self.driver.session() as session:
            # First clear database (optional - uncomment if you want)
            # session.run("MATCH (n) DETACH DELETE n")
            
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row in csv_reader:
                    # Create project (if doesn't exist)
                    session.run("""
                        MERGE (p:Project {id: $project_id})
                        ON CREATE SET p.name = $project_name
                    """,
                        project_id=row['project_id'],
                        project_name=row['project_name']
                    )
                    
                    # Create student
                    session.run("""
                        MERGE (s:Student {index: $index})
                        ON CREATE SET 
                            s.name = $name,
                            s.surname = $surname,
                            s.github = $github
                    """,
                        index=(row['index']),
                        name=row['name'],
                        surname=row['surname'],
                        github=row['github']
                    )
                    
                    # Create belongs_to relationship
                    session.run("""
                        MATCH (s:Student {index: $index})
                        MATCH (p:Project {id: $project_id})
                        MERGE (s)-[r:belongs_to]->(p)
                        ON CREATE SET r.role = $role
                    """,
                        index=row['index'],
                        project_id=row['project_id'],
                        role=row['role']
                    )
            
            print("Database filled successfully!")

    def clear_database(self):
        """
        Clear entire database
        """
        with self.driver.session() as session:
            result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
            deleted_count = result.single()['deleted']
            print(f"Deleted {deleted_count} nodes with relationships")


#test functions for methods
if __name__ == "__main__":   
    retriever = Neo4jRetriever() # initialize retriever

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------GET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    # print(retriever.get_students())
    # print(retriever.get_project_grades(project_id="2"))
    # print(retriever.get_member_grades(index="2006"))
    # print(retriever.is_leader(index="2007"))
    # print(retriever.get_project_members(project_id="2"))
    # print(retriever.get_user_info(index="2006"))
    # print(retriever.has_graded_all_members(index="2007"))
    # print(retriever.get_ungraded_members(index="2007"))
    # print(retriever.has_graded_all_projects(index="2007"))
    # print(retriever.get_ungraded_projects(index="2007"))

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------SET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    # print(retriever.set_self_grade(grading_person_index = "2007", grade = 4.5, description = "Dobra praca, ale mogę się jeszcze poprawić"))
    # print(retriever.set_teammate_grade(grading_person_index = "2007", graded_person_index = "2006", grade = 3.5, description="Solidna praca, ale wymaga poprawy w niektórych obszarach"))
    # print(retriever.set_leader_grade(grading_person_index = "2007", project_id = "2", grade = 3.5, description="Świetna prowadził pracę zespołu i dostarczył wartościowe wyniki"))
    # print(retriever.set_project_grade(grading_person_index = "2007", project_id = "2", grade=4.5, description="Projekt został zrealizowany zgodnie z założeniami"))
    # print(retriever.set_project_objectives_grade(grading_person_index = "2007", project_id = "2", grade=5.0, description="Założenia były jasno określone i realistyczne"))

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------FILL THE BASE---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    #retriever.clear_database()
    retriever.fill_database_no_grades("src/neo4j_retriever/data_no_grades.csv")
    # retriever.fill_database_with_grades("src/neo4j_retriever/grades.csv")
    retriever.close() # destroy retriever
