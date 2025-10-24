from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

#to solve problems with .env path
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent.parent / '.env') #path set for .env in the root directory

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

    def get_project_grades(self, project_id: int):
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

    def get_member_grades(self, index: int):
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

    def is_leader(self, index: int):
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

    def get_project_members(self, project_id: int):
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

    def get_user_info(self, index: int):
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

    def has_graded_all_members(self, index: int):
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

    def get_ungraded_members(self, index: int):
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
                RETURN teammate.index as ungraded_index
                ORDER BY teammate.index
            """, index=index)
            
            return [record["ungraded_index"] for record in result]

    def has_graded_all_projects(self, index: int):
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

    def get_ungraded_projects(self, index: int):
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

    def close(self):
        self.driver.close()

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------SET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def set_self_grade(
        self, 
        grading_person_index: int,
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
    grading_person_index: int,
    graded_person_index: int,
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
        grading_person_index: int,
        project_id: int,
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
        grading_person_index: int,
        project_id: int,
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
        grading_person_index: int,
        project_id: int,
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
                    grader_id = int(row['grader_id'])
                    project_id = int(row['project_id']) if row.get('project_id') and row['project_id'].strip() else None
                    graded_id = int(row['graded_id']) if row.get('graded_id') and row['graded_id'].strip() else None
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
                        project_id=int(row['project_id']),
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
                        index=int(row['index']),
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
                        index=int(row['index']),
                        project_id=int(row['project_id']),
                        role=row['role']
                    )
            
            print("Database filled successfully!")

    def clear_database(self):
        """
        Clear entire database (WARNING: deletes all data!)
        """
        with self.driver.session() as session:
            result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
            deleted_count = result.single()['deleted']
            print(f"Deleted {deleted_count} nodes with relationships")


# Complete test suite for Neo4j retriever
if __name__ == "__main__":   
    retriever = Neo4jRetriever() # Initialize retriever

    print("=" * 80)
    print("COMPLETE NEO4J RETRIEVER TEST SUITE")
    print("=" * 80)

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------STEP 1: DATABASE INITIALIZATION------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    print("\n🔄 STEP 1: DATABASE INITIALIZATION")
    print("-" * 50)
    
    print("1.1 Clearing existing database...")
    try:
        retriever.clear_database()
        print("✅ Database cleared successfully")
    except Exception as e:
        print(f"❌ Error clearing database: {e}")

    print("\n1.2 Loading students and projects from CSV...")
    try:
        script_dir = Path(__file__).parent
        data_file = script_dir / "data_no_grades.csv"
        retriever.fill_database_no_grades(str(data_file))
        print("✅ Students and projects loaded successfully")
    except Exception as e:
        print(f"❌ Error loading base data: {e}")

    print("\n1.3 Loading grades from CSV...")
    try:
        script_dir = Path(__file__).parent
        grades_file = script_dir / "grades.csv"
        retriever.fill_database_with_grades(str(grades_file))
        print("✅ Grades loaded successfully")
    except Exception as e:
        print(f"❌ Error loading grades: {e}")

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------STEP 2: BASIC DATA VERIFICATION------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    print("\n\n📊 STEP 2: BASIC DATA VERIFICATION")
    print("-" * 50)

    print("\n2.1 Testing get_students():")
    try:
        students = retriever.get_students()
        print(f"✅ Found {len(students)} students")
        if students:
            print(f"   First student: {students[0]}")
            print(f"   Last student: {students[-1]}")
    except Exception as e:
        print(f"❌ Error: {e}")

    print("\n2.2 Testing project members:")
    for project_id in [1, 2]:
        try:
            members = retriever.get_project_members(project_id=project_id)
            print(f"✅ Project {project_id} has {len(members)} members: {members}")
        except Exception as e:
            print(f"❌ Error getting project {project_id} members: {e}")

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------STEP 3: LEADERSHIP AND USER INFO TESTING--------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    print("\n\n👑 STEP 3: LEADERSHIP AND USER INFO TESTING")
    print("-" * 50)

    print("\n3.1 Testing leadership status:")
    test_indexes = [2001, 2002, 2003, 2006, 2007]
    leaders_found = []
    for idx in test_indexes:
        try:
            is_leader = retriever.is_leader(index=idx)
            status = "👑 LEADER" if is_leader else "👤 Member"
            print(f"   Student {idx}: {status}")
            if is_leader:
                leaders_found.append(idx)
        except Exception as e:
            print(f"❌ Error testing student {idx}: {e}")
    
    print(f"✅ Found {len(leaders_found)} leaders: {leaders_found}")

    print("\n3.2 Testing user info for key students:")
    for idx in [2001, 2006]:  # One from each project
        try:
            user_info = retriever.get_user_info(index=idx)
            if user_info:
                print(f"✅ Student {idx}: {user_info['name']} {user_info['surname']}")
                print(f"   Project: {user_info['project_name']} (ID: {user_info['project_id']})")
            else:
                print(f"❌ No info found for student {idx}")
        except Exception as e:
            print(f"❌ Error getting info for student {idx}: {e}")

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------STEP 4: GRADING DATA VERIFICATION---------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    print("\n\n📝 STEP 4: GRADING DATA VERIFICATION")
    print("-" * 50)

    print("\n4.1 Testing project grades:")
    for project_id in [1, 2]:
        try:
            project_grades = retriever.get_project_grades(project_id=project_id)
            internal_grades = [g for g in project_grades if g['was_member']]
            external_grades = [g for g in project_grades if not g['was_member']]
            
            print(f"✅ Project {project_id}: {len(project_grades)} total grades")
            print(f"   - Internal grades (team members): {len(internal_grades)}")
            print(f"   - External grades (other students): {len(external_grades)}")
            
            if project_grades:
                avg_grade = sum(g['grade'] for g in project_grades) / len(project_grades)
                print(f"   - Average grade: {avg_grade:.2f}")
                
        except Exception as e:
            print(f"❌ Error getting grades for project {project_id}: {e}")

    print("\n4.2 Testing member grades (teammate assessments):")
    for idx in [2001, 2003, 2006]:  # Test various students
        try:
            member_grades = retriever.get_member_grades(index=idx)
            leader_grades = [g for g in member_grades if g['is_leader']]
            
            print(f"✅ Student {idx}: {len(member_grades)} teammate grades received")
            print(f"   - Grades from leaders: {len(leader_grades)}")
            
            if member_grades:
                avg_grade = sum(g['grade'] for g in member_grades) / len(member_grades)
                print(f"   - Average teammate grade: {avg_grade:.2f}")
                
        except Exception as e:
            print(f"❌ Error getting member grades for student {idx}: {e}")

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------STEP 5: COMPLETION STATUS TESTING---------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    print("\n\n✅ STEP 5: COMPLETION STATUS TESTING")
    print("-" * 50)

    print("\n5.1 Testing teammate grading completion:")
    completed_teammate_grading = 0
    total_students = 0
    
    for idx in test_indexes:
        try:
            has_graded_all = retriever.has_graded_all_members(index=idx)
            ungraded = retriever.get_ungraded_members(index=idx)
            
            status = "✅ COMPLETE" if has_graded_all else f"❌ INCOMPLETE ({len(ungraded)} ungraded)"
            print(f"   Student {idx}: {status}")
            
            if has_graded_all:
                completed_teammate_grading += 1
            total_students += 1
            
        except Exception as e:
            print(f"❌ Error checking completion for student {idx}: {e}")
    
    print(f"✅ Teammate grading completion: {completed_teammate_grading}/{total_students} students")

    print("\n5.2 Testing project grading completion:")
    completed_project_grading = 0
    
    for idx in test_indexes:
        try:
            has_graded_all_projects = retriever.has_graded_all_projects(index=idx)
            ungraded_projects = retriever.get_ungraded_projects(index=idx)
            
            status = "✅ COMPLETE" if has_graded_all_projects else f"❌ INCOMPLETE ({len(ungraded_projects)} ungraded)"
            print(f"   Student {idx}: {status}")
            
            if has_graded_all_projects:
                completed_project_grading += 1
                
        except Exception as e:
            print(f"❌ Error checking project completion for student {idx}: {e}")
    
    print(f"✅ Project grading completion: {completed_project_grading}/{total_students} students")

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------STEP 6: FINAL SUMMARY----------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    print("\n\n🎯 STEP 6: FINAL SUMMARY")
    print("-" * 50)
    
    try:
        # Final statistics
        all_students = retriever.get_students()
        project1_members = retriever.get_project_members(project_id=1)
        project2_members = retriever.get_project_members(project_id=2)
        project1_grades = retriever.get_project_grades(project_id=1)
        project2_grades = retriever.get_project_grades(project_id=2)
        
        print(f"📊 Database Statistics:")
        print(f"   - Total students: {len(all_students)}")
        print(f"   - Project 1 members: {len(project1_members)}")
        print(f"   - Project 2 members: {len(project2_members)}")
        print(f"   - Project 1 grades: {len(project1_grades)}")
        print(f"   - Project 2 grades: {len(project2_grades)}")
        print(f"   - Leaders found: {len(leaders_found)}")
        
        print(f"\n✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("🚀 Neo4j Retriever is ready for production use!")
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")

    print("\n" + "=" * 80)
    print("TEST SUITE FINISHED")
    print("=" * 80)
    
    retriever.close() # Close connection
