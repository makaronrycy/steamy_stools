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
    def get_completion_status(self):
        """
        Get completion status of all students
        
        Returns:
            dict: Completion status
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (all_students:Student)
                WITH COUNT(all_students) as total_students
                OPTIONAL MATCH (completed_student:Student)-[:HAS_SESSION]->(cs:ConversationSession)
                WHERE cs.current_state IN ["completed", "done"] OR cs.completed = true
                WITH total_students, COUNT(DISTINCT completed_student) as completed_students
                RETURN completed_students, 
                total_students,
                total_students - completed_students as remaining_students,
                ROUND(100.0 * completed_students / total_students, 2) as completion_percentage"""
            ).single()
            return {
                "completed_students": result["completed_students"],
                "total_students": result["total_students"],
                "remaining_students": result["remaining_students"],
                "completion_percentage": result["completion_percentage"]
            }
                
    def is_member_of_project(self, student_index: str, project_id: str) -> bool:
        """
        Check if a student is a member of a given project
        
        Args:
            student_index: Student index
            project_id: Project ID
        Returns:
            bool: True if student is a member of the project
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})-[:belongs_to]->(project:Project {id: $project_id})
                RETURN COUNT(project) > 0 as is_member
            """, student_index=student_index, project_id=project_id)
            
            record = result.single()
            return record["is_member"] if record else False
    def list_people(self):
        response = []
        with self.driver.session() as session:
            projects = session.run("Match (p:Project) RETURN p.id as id, p.name as name ORDER BY p.id").data()

        for record in projects:
            payload = {}
            payload['project_id'] = record['id']
            payload['project_name'] = record['name']
            payload['people'] = []

            with self.driver.session() as session:
                people_for_project = session.run("""
                    MATCH (s:Student)-[:belongs_to]->(p:Project {id: $project_id})
                    RETURN s.name AS name, s.surname AS surname, s.index AS index
                    ORDER BY s.index
                """, project_id=record['id']).data()

            for person_record in people_for_project:
                person_payload = {
                    'name': person_record['name'],
                    'surname': person_record['surname'],
                    'index': person_record['index']
                }
                payload['people'].append(person_payload)
            response.append(payload)
        return response
    def get_id_by_name(self, name: str, surname: str = None):
        """
        Get student ID (index) by name and optional surname
        
        Args:
            name: Student name
            surname: Student surname (optional)
            
        Returns:
            str: Student index or None
        """
        where_statement = "WHERE toLower(s.name) = toLower($name)"
        if surname:
            where_statement += " AND toLower(s.surname) = toLower($surname)"
            
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (s:Student)
                {where_statement}
                RETURN s.index as index
            """, name=name, surname=surname)
            
            record = result.single()
            return record["index"] if record else None

    def get_node_types(self):
        return {"node_types": []}
    
    def get_latest_teammate_answer_meta(self, grading_person_index: str, graded_person_index: str) -> dict | None:
        """
        Returns latest teammate_assessment answer meta for (grader -> graded).
        Uses id(a) ordering so it works even without timestamps.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $grading_person_index})-[:answered]->(a:Answer)-[:refers_to]->(graded:Student {index: $graded_person_index})
                WHERE a.question_type = "teammate_assessment"
                RETURN a.grade AS grade,
                    a.explanation AS explanation,
                    coalesce(a.outlier_followup_done, false) AS outlier_followup_done
                ORDER BY id(a) DESC
                LIMIT 1
            """, grading_person_index=grading_person_index, graded_person_index=graded_person_index)
            rec = result.single()
            if not rec:
                return None
            return {
                "grade": rec["grade"],
                "explanation": rec["explanation"],
                "outlier_followup_done": rec["outlier_followup_done"],
            }

    def append_teammate_outlier_followup(self, grading_person_index: str, graded_person_index: str, followup: str) -> bool:
        """
        Appends outlier follow-up to the latest teammate_assessment answer and marks followup done.
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $grading_person_index})-[:answered]->(a:Answer)-[:refers_to]->(graded:Student {index: $graded_person_index})
                WHERE a.question_type = "teammate_assessment"
                WITH a
                ORDER BY id(a) DESC
                LIMIT 1
                SET a.outlier_followup = $followup,
                    a.outlier_followup_done = true,
                    a.explanation = coalesce(a.explanation, "") + "\n\n[Dodatkowe uzasadnienie - outlier]: " + $followup
                RETURN true AS ok
            """, grading_person_index=grading_person_index, graded_person_index=graded_person_index, followup=followup)
            rec = result.single()
            return bool(rec and rec["ok"])

    
    def get_students(self):
        with self.driver.session() as session:
            result = session.run("MATCH (s:Student) RETURN s.name AS name, s.surname AS surname, s.index AS index")
            return [{"name": record["name"], "surname": record["surname"], "index": record["index"]} for record in result]
    
    def get_student_project(self, index: str):
        """Get the project that student belongs to"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $index})-[:belongs_to]->(project:Project)
                RETURN project.id AS project_id, project.name AS project_name
            """, index=index)
            record = result.single()
            if record:
                return {"project_id": record["project_id"], "project_name": record["project_name"]}
            return None

    def get_leader_of_student(self, index: str):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (leader:Student)-[r:belongs_to]->(project)
                WHERE r.role = "leader"
                RETURN leader.name AS name, leader.surname AS surname, leader.index AS index, project.id AS project_id
            """, index=index)
            record = result.single()
            if record:
                return {"name": record["name"], "surname": record["surname"], "index": record["index"], "project_id": record["project_id"]}
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

    def get_member_grades(self, name: str):
        """
        Get grades for a given member (index) and mark whether grader is leader in the same project.
        Returns: grade, explanation, grader_index, is_leader
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (graded:Student {name: $name})
                OPTIONAL MATCH (graded)-[:belongs_to]->(p:Project)

                OPTIONAL MATCH (grader:Student)-[:answered]->(answer:Answer)-[:refers_to]->(graded)
                WHERE answer.question_type = "teammate_assessment"

                // leader relationship only used for flagging, NOT filtering results
                OPTIONAL MATCH (grader)-[lr:belongs_to {role: "leader"}]->(p)

                RETURN answer.grade as grade,
                    answer.explanation as explanation,
                    grader.index as grader_index,
                    CASE WHEN lr IS NOT NULL THEN true ELSE false END as is_leader
                ORDER BY grader.index
            """, name=name)

            return [
                {
                    "grade": record["grade"],
                    "explanation": record["explanation"],
                    "grader_index": record["grader_index"],
                    "is_leader": record["is_leader"],
                }
                for record in result
            ]


    def is_leader(self, name: str):
        """
        Check if student is a leader
        
        Args:
            name: Student name
            
        Returns:
            bool: True if student is a leader
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {name: $name})-[r:belongs_to]->(project:Project)
                WHERE r.role = "leader"
                RETURN COUNT(r) > 0 as is_leader
            """, name=name)
            
            record = result.single()
            return record["is_leader"] if record else False

    def get_project_members(self, project_id: str):
        """
        Get all member indexes from a given project (excluding leader)
        
        Args:
            project_id: Project ID
            
        Returns:
            List of project member indexes
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student)-[r:belongs_to]->(project:Project {id: $project_id})
                WHERE r.role <> "leader"
                RETURN student.index as index
                ORDER BY student.index
            """, project_id=project_id)
            
            return [record["index"] for record in result]

    def get_user_info(self, name: str):
        """
        Get user information
        
        Args:
            name: Student name
            
        Returns:
            Dictionary with user information
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {name: $name})
                OPTIONAL MATCH (student)-[:belongs_to]->(project:Project)
                RETURN student.name as name,
                       student.surname as surname,
                       student.github as github,
                       project.id as project_id,
                       project.name as project_name
            """, name=name)
            
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

    def has_graded_all_members(self, name: str):
        """
        Check if user has graded all team members
        
        Args:
            name: Grader name
            
        Returns:
            bool: True if graded all team members
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {name: $name})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.name <> $name
                WITH grader, collect(teammate.index) as all_teammates
                OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(graded:Student)
                WHERE answer.question_type = "teammate_assessment"
                WITH all_teammates, collect(graded.index) as graded_teammates
                RETURN size(all_teammates) = size(graded_teammates) AND size(all_teammates) > 0 as has_graded_all
            """, name=name)
            
            record = result.single()
            return record["has_graded_all"] if record else False

    def get_ungraded_members(self, name: str):
        """
        Get list of ungraded team members
        
        Args:
            name: Grader name
            
        Returns:
            List of indexes of ungraded members
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {name: $name})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.name <> $name
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
            """, name=name)
            
            return [{"index": record["ungraded_index"], "name": record["name"], "surname": record["surname"]} for record in result]
        
    def get_random_ungraded_member(self, index: str):
        """
        Deterministic: returns the next ungraded teammate ordered by teammate.index
        (we keep the name for compatibility with existing tools/prompts).
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {index: $index})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.index <> $index
                AND NOT EXISTS {
                    MATCH (grader)-[:answered]->(a:Answer)-[:refers_to]->(teammate)
                    WHERE a.question_type = "teammate_assessment"
                }
                RETURN teammate.index as index, teammate.name as name, teammate.surname as surname
                ORDER BY teammate.index
                LIMIT 1
            """, index=index)

            record = result.single()
            if not record:
                return None
            return {"index": record["index"], "name": record["name"], "surname": record["surname"]}

    def has_graded_all_projects(self, name: str):
        """
        Check if user has graded all projects
        
        Args:
            name: Grader name
            
        Returns:
            bool: True if graded all projects
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project)
                WITH collect(project.id) as all_projects
                MATCH (grader:Student {name: $name})
                OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(graded_project:Project)
                WHERE answer.question_type = "project_assessment"
                WITH all_projects, collect(graded_project.id) as graded_projects
                RETURN size(all_projects) = size(graded_projects) AND size(all_projects) > 0 as has_graded_all
            """, name=name)
            
            record = result.single()
            return record["has_graded_all"] if record else False

    def get_ungraded_projects(self, name: str):
        """
        Get list of ungraded projects

        Args:
            name: Grader name

        Returns:
            List of ungraded project IDs
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {name: $name})
                MATCH (project:Project)
                WHERE NOT EXISTS {
                    MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(project)
                    WHERE answer.question_type = "project_assessment"
                }
                RETURN
                    project.id as ungraded_project_id,
                    project.name as project_name
                ORDER BY project.id
            """, name=name)

            return [{"project_id": record["ungraded_project_id"], "project_name": record["project_name"]} for record in result]
        
    def get_student_completion_status(self, name: str):
        """
        Check completion status of all answer types for a given student
        
        Args:
            name: Student name
            
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
                },
                "assumption_evaluations": {
                    "total_required": int (only assumptions where system_accepted=false),
                    "completed": int,
                    "is_complete": bool,
                    "incomplete_details": [
                        {
                            "assumption_description": str,
                            "has_explanation": bool
                        }
                    ]
                }
            }
        """
        with self.driver.session() as session:
            result = {}
            
            # 1. SELF ASSESSMENT
            self_result = session.run("""
                MATCH (student:Student {name: $name})
                OPTIONAL MATCH (student)-[:answered]->(answer:Answer)-[:refers_to]->(student)
                WHERE answer.question_type = "self_assessment"
                RETURN answer.grade as grade, 
                       answer.explanation as explanation
            """, name=name)
            
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
                MATCH (grader:Student {name: $name})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.name <> $name
                RETURN teammate.index as teammate_index
                ORDER BY teammate.index
            """, name=name)
            
            all_teammates = [record["teammate_index"] for record in teammates_result]
            total_teammates = len(all_teammates)
            
            incomplete_teammates = []
            completed_teammates = 0
            
            for teammate_idx in all_teammates:
                teammate_answer = session.run("""
                    MATCH (grader:Student {name: $grader_name})
                    MATCH (teammate:Student {index: $teammate_index})
                    OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(teammate)
                    WHERE answer.question_type = "teammate_assessment"
                    RETURN answer.grade as grade,
                           answer.explanation as explanation
                    ORDER BY id(answer) DESC
                    LIMIT 1
                """, grader_name=name, teammate_index=teammate_idx).single()
                
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
                    MATCH (grader:Student {name: $name})
                    MATCH (project:Project {id: $project_id})
                    OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(project)
                    WHERE answer.question_type = "project_assessment"
                    RETURN answer.grade as grade,
                           answer.explanation as explanation
                """, name=name, project_id=proj_id).single()
                
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
                MATCH (grader:Student {name: $name})-[:belongs_to]->(project:Project)
                MATCH (leader:Student)-[r:belongs_to]->(project)
                WHERE r.role = "leader"
                RETURN leader.index as leader_index
            """, name=name)
            
            leadership_record = leadership_result.single()
            
            if leadership_record:
                leader_idx = leadership_record["leader_index"]
                leadership_answer = session.run("""
                    MATCH (grader:Student {name: $name})
                    MATCH (leader:Student {index: $leader_index})
                    OPTIONAL MATCH (grader)-[:answered]->(answer:Answer)-[:refers_to]->(leader)
                    WHERE answer.question_type = "leadership_assessment"
                    RETURN answer.grade as grade,
                           answer.explanation as explanation
                """, name=name, leader_index=leader_idx).single()
                
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
                MATCH (student:Student {name: $name})-[:belongs_to]->(project:Project)
                OPTIONAL MATCH (student)-[:answered]->(answer:Answer)-[:refers_to]->(project)
                WHERE answer.question_type = "objectives_assessment"
                RETURN project.id as project_id,
                       answer.grade as grade,
                       answer.explanation as explanation
            """, name=name)
            
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

            # 6. MASTERS INTENT (open answer)
            masters_result = session.run("""
                MATCH (student:Student {name: $name})
                OPTIONAL MATCH (student)-[:answered]->(answer:Answer)-[:refers_to]->(student)
                WHERE answer.question_type = "masters_intent"
                RETURN answer.explanation as explanation
            """, name=name)
            masters_record = masters_result.single()
            masters_expl = masters_record["explanation"] if masters_record else None
            masters_has_answer = masters_expl is not None and str(masters_expl).strip() != ""
            result["masters_intent"] = {
                "has_answer": masters_has_answer,
                "is_complete": masters_has_answer,
            }

            # 7. STUDY PROGRAM FEEDBACK (open answer)
            feedback_result = session.run("""
                MATCH (student:Student {name: $name})
                OPTIONAL MATCH (student)-[:answered]->(answer:Answer)-[:refers_to]->(student)
                WHERE answer.question_type = "study_program_feedback"
                RETURN answer.explanation as explanation
            """, name=name)
            feedback_record = feedback_result.single()
            feedback_expl = feedback_record["explanation"] if feedback_record else None
            feedback_has_answer = feedback_expl is not None and str(feedback_expl).strip() != ""
            result["study_program_feedback"] = {
                "has_answer": feedback_has_answer,
                "is_complete": feedback_has_answer,
            }

            # 8. ASSUMPTION EVALUATIONS
            # Get all assumptions for the student's project and check which are evaluated
            assumptions_result = session.run("""
                MATCH (student:Student {name: $name})-[:belongs_to]->(project:Project)
                MATCH (project)-[:has_assumption]->(assumption:Assumption)
                OPTIONAL MATCH (student)-[:evaluated]->(eval:AssumptionEvaluation)-[:refers_to]->(assumption)
                RETURN elementId(assumption) as assumption_id,
                       assumption.description as description,
                       eval.explanation as explanation
                ORDER BY elementId(assumption)
            """, name=name)

            all_assumptions = []
            incomplete_assumptions = []
            completed_assumptions = 0

            for record in assumptions_result:
                assumption_info = {
                    "assumption_id": record["assumption_id"],
                    "description": record["description"],
                    "has_evaluation": record["explanation"] is not None,
                    "has_explanation": record["explanation"] is not None and str(record["explanation"]).strip() != ""
                }
                all_assumptions.append(assumption_info)

                if assumption_info["has_evaluation"] and assumption_info["has_explanation"]:
                    completed_assumptions += 1
                else:
                    incomplete_assumptions.append(assumption_info)

            total_assumptions = len(all_assumptions)
            result["assumption_evaluations"] = {
                "total_required": total_assumptions,
                "completed": completed_assumptions,
                "is_complete": completed_assumptions == total_assumptions and total_assumptions > 0,
                "incomplete_details": incomplete_assumptions
            }
            
            # 6. ASSUMPTION EVALUATIONS (only for system_accepted = false)
            # Get all assumptions that the system rejected (require student evaluation)
            assumptions_result = session.run("""
                MATCH (student:Student {name: $name})-[:belongs_to]->(project:Project)
                MATCH (project)-[:has_assumption]->(assumption:Assumption)
                WHERE assumption.system_accepted = false
                OPTIONAL MATCH (student)-[:evaluated]->(eval:AssumptionEvaluation)-[:refers_to]->(assumption)
                RETURN elementId(assumption) as assumption_id,
                       assumption.description as description,
                       assumption.system_accepted as system_accepted,
                       project.id as project_id,
                       project.name as project_name,
                       eval.explanation as explanation
                ORDER BY elementId(assumption)
            """, name=name)
            
            all_rejected_assumptions = []
            incomplete_assumptions = []
            completed_assumptions = 0
            
            for record in assumptions_result:
                assumption_id = record["assumption_id"]
                description = record["description"]
                system_accepted = record["system_accepted"]
                project_id = record["project_id"]
                project_name = record["project_name"]
                explanation = record["explanation"]
                has_evaluation = explanation is not None
                has_explanation = explanation is not None and str(explanation).strip() != ""
                
                assumption_info = {
                    "assumption_id": assumption_id,
                    "description": description,
                    "system_accepted": system_accepted,
                    "project_id": project_id,
                    "project_name": project_name,
                    "has_evaluation": has_evaluation,
                    "has_explanation": has_explanation
                }
                all_rejected_assumptions.append(assumption_info)
                
                if has_evaluation and has_explanation:
                    completed_assumptions += 1
                else:
                    incomplete_assumptions.append(assumption_info)
            
            total_rejected = len(all_rejected_assumptions)
            
            result["assumption_evaluations"] = {
                "total_required": total_rejected,
                "completed": completed_assumptions,
                "is_complete": completed_assumptions == total_rejected,
                "incomplete_details": incomplete_assumptions
            }
            
            result["all_complete"] = (
                result["self_assessment"]["is_complete"] and
                result["teammate_assessments"]["is_complete"] and
                result["project_assessments"]["is_complete"] and
                result["leadership_assessment"]["is_complete"] and
                result["objectives_assessment"]["is_complete"] and
                result["masters_intent"]["is_complete"] and
                result["study_program_feedback"]["is_complete"] and
                result["assumption_evaluations"]["is_complete"]
            )
            
            return result

    def identify_teammate_by_name(self, grader_name: str, name: str,surname: str|None):
        """
        Identify teammates by name from the same project
        
        Args:
            grader_name: Name of the student searching
            name: Name to search for
            
        Returns:
            List of dicts: [{"name": str, "surname": str, "index": str}]
        """
        where_statement = "AND toLower(teammate.name) = toLower($name)"
        if surname is not None:
            where_statement += " AND toLower(teammate.surname) = toLower($surname)"
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {name: $grader_name})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.name <> $grader_name 
                    """ + where_statement + """
                        RETURN teammate.name AS name, 
                       teammate.surname AS surname, 
                       teammate.index AS index
                ORDER BY teammate.surname, teammate.name
            """, grader_name=grader_name, name=name,surname=surname)
            
            return [{"name": record["name"], 
                    "surname": record["surname"], 
                    "index": record["index"]} for record in result]

    def identify_teammate_by_surname(self, grader_name: str, surname: str):
        """
        Identify teammates by surname from the same project

        Args:
            grader_name: Name of the student searching
            surname: Surname to search for

        Returns:
            List of dicts: [{"name": str, "surname": str, "index": str}]
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (grader:Student {name: $grader_name})-[:belongs_to]->(project:Project)
                MATCH (teammate:Student)-[:belongs_to]->(project)
                WHERE teammate.name <> $grader_name
                  AND toLower(teammate.surname) = toLower($surname)
                RETURN teammate.name AS name,
                       teammate.surname AS surname,
                       teammate.index AS index
                ORDER BY teammate.surname, teammate.name
            """, grader_name=grader_name, surname=surname)

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
    def get_unevaluated_assumptions(self, student_index: str):
        """
        Get assumptions the student hasn't evaluated yet (from their project).
        Only returns assumptions where system_accepted = false (requiring student evaluation).

        Args:
            student_index: Student index

        Returns:
            List of unevaluated assumptions with their actual fulfillment status
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})-[:belongs_to]->(project:Project)
                MATCH (project)-[:has_assumption]->(assumption:Assumption)
                OPTIONAL MATCH (student)-[:evaluated]->(eval:AssumptionEvaluation)-[:refers_to]->(assumption)
                WITH student, project, assumption, eval
                WHERE eval IS NULL
                RETURN elementId(assumption) as assumption_id,
                       assumption.description as description,
                       assumption.system_accepted as system_accepted,
                       project.id as project_id,
                       project.name as project_name
                ORDER BY elementId(assumption)
            """, student_index=student_index)

            return [{"assumption_id": record["assumption_id"],
                    "description": record["description"],
                    "system_accepted": record["system_accepted"],
                    "project_id": record["project_id"],
                    "project_name": record["project_name"]} for record in result]
    def create_conversation_session(self, student_index: str):
        import uuid
        with self.driver.session() as session:
            session_id = str(uuid.uuid4())
            result = session.run("""
                MATCH (student:Student {index: $student_index})
                CREATE (cs:ConversationSession {
                    session_id: $session_id,
                    student_index: $student_index,
                    current_state: "initial",
                    last_state: null,
                    pending_target_json: null,
                    pending_substate_json: null,
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
                    cs.pending_target_json as pending_target_json,
                    cs.pending_substate_json as pending_substate_json,
                    cs.started_at as started_at,
                    cs.last_updated as last_updated,
                    cs.is_active as is_active,
                    cs.completed as completed
            """, student_index=student_index, session_id=session_id)

            record = result.single()
            if record:
                return {
                    "session_id": record["session_id"],
                    "student_index": record["student_index"],
                    "current_state": record["current_state"],
                    "last_state": record["last_state"],
                    "pending_target_json": record["pending_target_json"],
                    "pending_substate_json": record["pending_substate_json"],
                    "started_at": record["started_at"],
                    "last_updated": record["last_updated"],
                    "is_active": record["is_active"],
                    "completed": record["completed"],
                }
        return None



    def get_active_session(self, student_index: str):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})-[:HAS_SESSION]->(cs:ConversationSession)
                WHERE cs.is_active = true AND cs.completed = false
                RETURN cs.session_id as session_id,
                    cs.student_index as student_index,
                    cs.current_state as current_state,
                    cs.last_state as last_state,
                    cs.pending_target_json as pending_target_json,
                    cs.pending_substate_json as pending_substate_json,
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
                    "pending_target_json": record["pending_target_json"],
                    "pending_substate_json": record["pending_substate_json"],
                    "started_at": record["started_at"],
                    "last_updated": record["last_updated"],
                    "is_active": record["is_active"],
                    "completed": record["completed"],
                }
        return None



    def update_session_state(
        self,
        session_id: str,
        new_state: str,
        pending_target_json: str | None = None,
        pending_substate_json: str | None = None,
    ):
        """
        Atomically: last_state <- current_state, current_state <- new_state,
        pending_target_json <- pending_target_json, pending_substate_json <- pending_substate_json
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (cs:ConversationSession {session_id: $session_id})
                SET cs.last_state = cs.current_state,
                    cs.current_state = $new_state,
                    cs.pending_target_json = $pending_target_json,
                    cs.pending_substate_json = $pending_substate_json,
                    cs.last_updated = datetime()
                RETURN cs.session_id as session_id
            """,
                session_id=session_id,
                new_state=new_state,
                pending_target_json=pending_target_json,
                pending_substate_json=pending_substate_json,
            )
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

    def get_conversation_history(self, session_id: str, limit = 5):
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
                ORDER BY cm.timestamp DESC
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

    def get_next_required_state(self, name: str):
        """
        Determine the next required state based on completion status

        Args:
            name: Student name

        Returns:
            dict: {
                "state": str (state name),
                "reason": str (why this state is next),
                "details": dict (additional context)
            }
        """
        status = self.get_student_completion_status(name)

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
            is_user_leader = self.is_leader(name)
            if not is_user_leader:  # Only non-leaders evaluate leadership
                return {
                    "next_state": "evaluate_leader_grade",
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

        # Priority 6: Assumption evaluations (only for assumptions NOT accepted by system)
        if not status["assumption_evaluations"]["is_complete"]:
            incomplete = status["assumption_evaluations"]["incomplete_details"]
            return {
                "next_state": "evaluate_assumption",
                "reason": "assumption_evaluations_incomplete",
                "details": {
                    "total_required": status["assumption_evaluations"]["total_required"],
                    "completed": status["assumption_evaluations"]["completed"],
                    "remaining": len(incomplete),
                    "next_assumption": incomplete[0] if incomplete else None
                }
            }
         # Priority 7: Masters intent (open answer)
        if not status.get("masters_intent", {}).get("is_complete", False):
            return {
                "next_state": "masters_intent",
                "reason": "masters_intent_incomplete",
                "details": {}
            }

        # Priority 8: Study program feedback (open answer)
        if not status.get("study_program_feedback", {}).get("is_complete", False):
            return {
                "next_state": "study_program_feedback",
                "reason": "study_program_feedback_incomplete",
                "details": {}
            }

        # All complete
        return {
            "next_state": "done",
            "reason": "all_assessments_complete",
            "details": {
                "completion_summary": status
            }
        }
    def get_student_project_id(self, index: str):
        """
        Get the project ID the student belongs to

        Args:
            name: Student name

        Returns:
            str: Project ID or None if not found
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $index})-[:belongs_to]->(project:Project)
                RETURN project.id as project_id
            """, index=index)

            record = result.single()
            if record:
                return record["project_id"]
            return None
    # REMOVED: This is a duplicate method, already defined above at line 878

    def has_evaluated_all_assumptions(self, student_index: str) -> bool:
        """
        Check if student has evaluated all assumptions from their project

        Args:
            student_index: Student index

        Returns:
            True if all assumptions evaluated, False otherwise
        """
        unevaluated = self.get_unevaluated_assumptions(student_index)
        return len(unevaluated) == 0

    def get_student_assumption_evaluation(self, student_index: str, assumption_id: str) -> dict | None:
        """
        Get a student's evaluation of a specific assumption

        Args:
            student_index: Student index
            assumption_id: Element ID of the assumption (from elementId())

        Returns:
            Evaluation dict or None if not evaluated
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})-[:evaluated]->(eval:AssumptionEvaluation)-[:refers_to]->(assumption:Assumption)
                WHERE elementId(assumption) = $assumption_id
                RETURN eval.fulfilled as fulfilled,
                       eval.explanation as explanation,
                       coalesce(eval.followup_done, false) as followup_done
            """, student_index=student_index, assumption_id=assumption_id)
            rec = result.single()
            if not rec:
                return None
            return {
                "fulfilled": rec["fulfilled"],
                "explanation": rec["explanation"],
                "followup_done": rec["followup_done"]
            }

    def get_project_assumptions_status(self, project_id: str) -> dict:
        """
        Get summary of project assumptions fulfillment status (ground truth)

        Args:
            project_id: Project ID

        Returns:
            dict with:
                - total: int - total number of assumptions
                - accepted_count: int - how many are accepted by system
                - rejected_count: int - how many are rejected by system
                - all_accepted: bool - whether all assumptions are accepted
                - assumptions: list - detailed list of assumptions with their status
        """
        assumptions = self.get_project_assumptions(project_id)

        accepted_count = sum(1 for a in assumptions if a.get("system_accepted") is True)
        rejected_count = len(assumptions) - accepted_count

        return {
            "total": len(assumptions),
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "all_accepted": rejected_count == 0 and len(assumptions) > 0,
            "assumptions": assumptions
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

    def set_github_grade(
        self,
        grading_person_index: str,
        graded_person_index: str,
        grade: float,
        description: str,
    ):
        """
        Save GitHub activity assessment

        Args:
            grading_person_index: Index number of the person grading
            graded_person_index: Index number of the person being graded
            grade: GitHub activity grade (e.g. 2.0-5.0)
            description: Justification for the grade
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (autor:Student {index: $grading_person_index}),
                    (oceniany:Student {index: $graded_person_index})
                CREATE (autor)-[:answered]->(o:Answer {
                    question_type: "github_assessment",
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

    def set_open_answer(self, student_index: str, question_type: str, answer: str):
        """Save a free-form interview answer linked to the student. Uses MERGE to prevent duplicates."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})
                MERGE (student)-[:answered]->(a:Answer {question_type: $question_type})-[:refers_to]->(student)
                ON CREATE SET a.grade = null, a.explanation = $answer
                ON MATCH SET a.explanation = $answer
                RETURN a.question_type as question_type,
                       a.explanation as explanation
            """, student_index=student_index, question_type=question_type, answer=answer)
            return result.single()

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------ASSUMPTION METHODS--------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def create_project_assumption(
        self,
        project_id,
        description: str,
        system_accepted: bool
    ):
        """
        Create a project assumption with its actual fulfillment status (ground truth)

        Args:
            project_id: Project ID
            assumption_id: Unique ID for the assumption
            name: Short name of the assumption
            description: Detailed description of the assumption
            fulfilled: True if assumption was actually fulfilled, False otherwise (ground truth)

        Returns:
            Created assumption information
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project {id: $project_id})
                CREATE (project)-[:has_assumption]->(assumption:Assumption {
                    description: $description,
                    system_accepted: $system_accepted
                })
                RETURN assumption.description as description,
                       assumption.system_accepted as system_accepted,
                       project.id as project_id,
                       project.name as project_name
            """,
                project_id=project_id,
                description=description,
                system_accepted=system_accepted
            )
            return result.single()

    def set_assumption_evaluation(
        self,
        student_index: str,
        assumption_index: str,
        fulfilled: bool,
        explanation: str
    ):
        """
        Student evaluates an assumption that was NOT accepted by the automated system.
        Students only evaluate assumptions where system_accepted = false.

        Args:
            student_index: Index of the student evaluating
            assumption_description: Description text of the assumption being evaluated
            fulfilled: Student's opinion - true if they believe assumption was fulfilled, false otherwise
            explanation: Student's explanation/opinion about why the assumption was/wasn't fulfilled

        Returns:
            Evaluation information
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {index: $student_index})-[:belongs_to]->(project:Project)
                MATCH (project)-[:has_assumption]->(assumption:Assumption)
                WHERE elementId(assumption) = $assumption_index
                CREATE (student)-[:evaluated]->(eval:AssumptionEvaluation {
                    fulfilled: $fulfilled,
                    explanation: $explanation
                })-[:refers_to]->(assumption)
                RETURN student.name as student_name,
                       student.surname as student_surname,
                       student.index as student_index,
                       elementId(assumption) as assumption_id,
                       assumption.description as assumption_description,
                       assumption.system_accepted as system_accepted,
                       eval.fulfilled as fulfilled,
                       eval.explanation as explanation
            """,
                student_index=student_index,
                assumption_index=assumption_index,
                fulfilled=fulfilled,
                explanation=explanation
            )
            return result.single()

    def get_assumption_evaluations(self, assumption_description: str):
        """
        Get all evaluations for a specific assumption
        
        Args:
            assumption_description: Description text of the assumption
            
        Returns:
            List of evaluations with student information
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (assumption:Assumption {description: $assumption_description})
                OPTIONAL MATCH (student:Student)-[:evaluated]->(eval:AssumptionEvaluation)-[:refers_to]->(assumption)
                RETURN student.index as student_index,
                       student.name as student_name,
                       student.surname as student_surname,
                       eval.explanation as explanation
                ORDER BY student.index
            """, assumption_description=assumption_description)
            
            return [{"student_index": record["student_index"],
                    "student_name": record["student_name"],
                    "student_surname": record["student_surname"],
                    "explanation": record["explanation"]} for record in result]

    def get_project_assumptions(self, project_id: str):
        """
        Get all assumptions for a specific project

        Args:
            project_id: Project ID

        Returns:
            List of assumptions with id, description and system_accepted status
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (project:Project {id: $project_id})-[:has_assumption]->(assumption:Assumption)
                RETURN elementId(assumption) as assumption_id,
                       assumption.description as description,
                       assumption.system_accepted as system_accepted
                ORDER BY assumption.description
            """, project_id=project_id)

            return [{"assumption_id": record["assumption_id"],
                    "description": record["description"],
                    "system_accepted": record["system_accepted"]} for record in result]

    def load_assumptions_from_json(self, json_path: str):
        """
        Load assumptions from JSON file for ALL projects based on project name mapping.
        Each assumption has description, system_accepted status, and projekt field.
        
        Args:
            json_path: Path to JSON file with format:
                [
                    {"projekt": "project_name", "opis": "description text", "spelnione": true/false},
                    ...
                ]
                
        Returns:
            dict: Summary of loaded assumptions per project
        """
        import json
        
        with open(json_path, 'r', encoding='utf-8') as file:
            assumptions_data = json.load(file)
        
        # Group assumptions by project name
        assumptions_by_project = {}
        for assumption in assumptions_data:
            project_name = assumption.get('projekt', '')
            if project_name:
                if project_name not in assumptions_by_project:
                    assumptions_by_project[project_name] = []
                assumptions_by_project[project_name].append(assumption)
        
        # Get project_id for each project_name from database
        project_name_to_id = {}
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Project)
                RETURN p.id as project_id, p.name as project_name
            """)
            for record in result:
                project_name_to_id[record['project_name']] = record['project_id']
        
        # Load assumptions for each project
        results = {}
        for project_name, assumptions in assumptions_by_project.items():
            project_id = project_name_to_id.get(project_name)
            if not project_id:
                print(f"Warning: Project '{project_name}' not found in database, skipping assumptions")
                continue
            
            created_count = 0
            accepted_count = 0
            rejected_count = 0
            
            for assumption in assumptions:
                description = assumption.get('opis', '')
                system_accepted = assumption.get('spelnione', False)
                
                if description:
                    self.create_project_assumption(
                        project_id=project_id,
                        description=description,
                        system_accepted=system_accepted
                    )
                    created_count += 1
                    if system_accepted:
                        accepted_count += 1
                    else:
                        rejected_count += 1
            
            print(f"Loaded {created_count} assumptions for project '{project_name}' (ID: {project_id})")
            print(f"  - System accepted: {accepted_count}")
            print(f"  - System rejected (require student evaluation): {rejected_count}")
            
            results[project_name] = {
                "project_id": project_id,
                "total_created": created_count,
                "system_accepted": accepted_count,
                "system_rejected": rejected_count
            }
        
        return results

    @staticmethod
    def generate_grades_with_assumptions(
        grades_csv_path: str,
        assumptions_json_path: str,
        output_csv_path: str
    ):
        """
        Generate a combined CSV file with grades and assumption definitions for ALL projects.
        Takes existing grades.csv and adds assumption_definition rows from JSON based on project name mapping.
        
        Args:
            grades_csv_path: Path to original grades CSV file
            assumptions_json_path: Path to JSON file with assumptions (must have "projekt" field)
            output_csv_path: Path for output combined CSV file
            
        Returns:
            dict: Summary of generated file per project
        """
        import csv
        import json
        
        # Read assumptions from JSON
        with open(assumptions_json_path, 'r', encoding='utf-8') as f:
            assumptions_data = json.load(f)
        
        # Read original grades CSV (skip comments and empty lines)
        original_rows = []
        with open(grades_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                # Skip comments and empty rows
                if row.get('type') and not row['type'].strip().startswith('#'):
                    original_rows.append(row)
        
        # Get project name to ID mapping from data_no_grades.csv
        # We need to read the CSV to know which project_id corresponds to which project_name
        project_name_to_id = {}
        data_csv_path = grades_csv_path.replace('grades.csv', 'data_no_grades.csv')
        try:
            with open(data_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or 'project_name' not in reader.fieldnames:
                    print(
                        f"Warning: {data_csv_path} missing 'project_name' column, "
                        "will use assumptions without project mapping"
                    )
                else:
                    for row in reader:
                        project_name_to_id[row['project_name']] = row['project_id']
        except FileNotFoundError:
            print(f"Warning: {data_csv_path} not found, will use assumptions without project mapping")
        
        # Generate assumption_definition rows grouped by project
        assumption_rows = []
        stats_by_project = {}
        
        for assumption in assumptions_data:
            description = assumption.get('opis', '')
            system_accepted = 1 if assumption.get('spelnione', False) else 0
            project_name = assumption.get('projekt', '')
            
            if description and project_name:
                project_id = project_name_to_id.get(project_name, '')
                
                if not project_id:
                    print(f"Warning: Project '{project_name}' not found in data_no_grades.csv")
                    continue
                
                assumption_rows.append({
                    'type': 'assumption_definition',
                    'grader_id': '',
                    'project_id': project_id,
                    'graded_id': description,
                    'grade': str(system_accepted),
                    'explanation': ''
                })
                
                # Track stats per project
                if project_name not in stats_by_project:
                    stats_by_project[project_name] = {'accepted': 0, 'rejected': 0, 'total': 0}
                stats_by_project[project_name]['total'] += 1
                if system_accepted:
                    stats_by_project[project_name]['accepted'] += 1
                else:
                    stats_by_project[project_name]['rejected'] += 1
        
        # Write combined CSV (no comments, clean format)
        with open(output_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # First write assumption definitions
            for row in assumption_rows:
                writer.writerow(row)
            
            # Then write original grades
            for row in original_rows:
                writer.writerow(row)
        
        return {
            "output_file": output_csv_path,
            "assumptions_added": len(assumption_rows),
            "original_grades": len(original_rows),
            "projects": stats_by_project
        }

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------FILL DATABASE-------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def fill_database_with_grades(self, csv_path: str):
        """
        Load all grades and assumption definitions from CSV file and add them to Neo4j database.

        Args:
            csv_path (str): Path to CSV file containing columns:
                type, grader_id, project_id, graded_id, grade, explanation
                
        Supported types:
            - self_assessment, teammate_assessment, leadership_assessment, 
              project_assessment, objectives_assessment, github_assessment
            - assumption_definition: defines project assumption (graded_id=description, grade=0/1 for system_accepted)
            - assumption_evaluation: student evaluates assumption (graded_id=description, explanation=student opinion)
        """
        import csv

        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            count = 0
            
            # First pass: create assumption definitions
            # We need to process assumption_definition rows first before evaluations
            assumptions_created = set()
            for row in csv_reader:
                if not row.get('type') or row['type'].strip().startswith('#'):
                    continue
                if row['type'].strip() == 'assumption_definition':
                    project_id = row['project_id'] if row.get('project_id') and row['project_id'].strip() else None
                    description = row['graded_id'] if row.get('graded_id') and row['graded_id'].strip() else None
                    system_accepted = bool(int(row.get('grade', 0))) if row.get('grade') else False
                    
                    if project_id and description:
                        assumption_key = f"{project_id}:{description}"
                        if assumption_key not in assumptions_created:
                            try:
                                self.create_project_assumption(
                                    project_id=project_id,
                                    description=description,
                                    system_accepted=system_accepted
                                )
                                assumptions_created.add(assumption_key)
                                count += 1
                                print(f"[{count}] Created assumption for project {project_id}: {description[:50]}...")
                            except Exception as e:
                                print(f"Error creating assumption: {e}")
            
            # Second pass: process all other grades
            file.seek(0)
            csv_reader = csv.DictReader(file)

            for row in csv_reader:
                # Skip rows with comments or empty rows
                if not row.get('type') or row['type'].strip().startswith('#'):
                    continue
                
                # Skip assumption_definition (already processed in first pass)
                if row['type'].strip() == 'assumption_definition':
                    continue
                
                # Skip rows with missing required data (except assumption_evaluation which doesn't need grade)
                grade_type = row['type'].strip()
                if grade_type != 'assumption_evaluation':
                    if not row.get('grader_id') or not row.get('grade'):
                        print(f"Skipping row with missing data: {row}")
                        continue
                else:
                    if not row.get('grader_id'):
                        print(f"Skipping row with missing grader_id: {row}")
                        continue
                
                try:
                    grader_id = row['grader_id']
                    project_id = row['project_id'] if row.get('project_id') and row['project_id'].strip() else None
                    graded_id = row['graded_id'] if row.get('graded_id') and row['graded_id'].strip() else None
                    grade = float(row['grade']) if row.get('grade') and row['grade'].strip() else 0
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

                    elif grade_type == "github_assessment" and graded_id:
                        self.set_github_grade(
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

                    elif grade_type == "assumption_evaluation":
                        # Student evaluates assumption that was rejected by system
                        # graded_id contains the assumption description
                        # grade field contains fulfilled status (1=fulfilled, 0=not fulfilled)
                        if graded_id:
                            self.set_assumption_evaluation(
                                student_index=grader_id,
                                assumption_description=graded_id,
                                fulfilled=bool(int(grade)) if grade else False,
                                explanation=explanation
                            )

                    count += 1
                    print(f"[{count}] Saved grade type '{grade_type}' from {grader_id}")

                except Exception as e:
                    print(f"Error saving grade type '{grade_type}' from {grader_id}: {e}")

        print(f"Completed! Loaded {count} grades from file '{csv_path}'")

    def fill_database_no_grades(self, csv_path: str, assumptions_json_path: str = None):
        """
        Fill database with students and projects from CSV file.
        Optionally load assumptions from JSON file.
        
        Args:
            csv_path: Path to CSV file
            assumptions_json_path: Optional path to JSON file with assumptions.
                                   If not provided, no assumptions are created.
        
        Format CSV:
            index,name,surname,github,project_id,project_name,role
            
        Format JSON (assumptions):
            [{"opis": "description", "spelnione": true/false}, ...]
        """
        import csv
        
        projects_created = set()
        
        with self.driver.session() as session:
            # First clear database (optional - uncomment if you want)
            # session.run("MATCH (n) DETACH DELETE n")
            
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                projects_created = set()
                for row in csv_reader:
                    # Create project (if doesn't exist)
                    session.run("""
                        MERGE (p:Project {id: $project_id})
                        ON CREATE SET p.name = $project_name
                    """,
                        project_id=row['project_id'],
                        project_name=row['project_name']
                    )
                    
                    # Track created projects for assumption loading
                    projects_created.add(row['project_id'])
                    
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
            
            print("Database filled with students and projects!")
            
            # Load assumptions from JSON if provided (automatically maps to projects by name)
            if assumptions_json_path:
                self.load_assumptions_from_json(assumptions_json_path)
            
            print("Database setup completed!")

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
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    retriever.clear_database()
    
    # Option 1: Fill database without grades (just students, projects, and assumptions from JSON)
    # JSON file maps assumptions to projects using "projekt" field
    retriever.fill_database_no_grades(
        "src/neo4j_retriever/data_no_grades_presentation.csv",
        "src/neo4j_retriever/raport_zgodnosci.json"
    )
    
    #Option 2: Generate combined CSV and fill with grades
    # Step 1: Generate grades_with_assumptions.csv from grades.csv + raport_zgodnosci.json
    # Automatically maps assumptions to projects based on "projekt" field in JSON
    Neo4jRetriever.generate_grades_with_assumptions(
         grades_csv_path="src/neo4j_retriever/grades_presentation.csv",
         assumptions_json_path="src/neo4j_retriever/raport_zgodnosci.json",
         output_csv_path="src/neo4j_retriever/grades_with_assumptions.csv"
     )
    # Step 2: Fill database from combined CSV
    retriever.fill_database_with_grades("src/neo4j_retriever/grades_with_assumptions.csv")
    
    retriever.close()
