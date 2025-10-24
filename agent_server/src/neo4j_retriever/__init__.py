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
        Zapisz samoocenę studenta
        
        Args:
            grading_person_index: Numer indeksu osoby oceniającej samą siebie
            grade: Ocena (np. 2-5)
            description: Uzasadnienie oceny
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
        Zapisz ocenę członka zespołu
        
        Args:
            grading_person_index: Numer indeksu osoby oceniającej
            graded_person_index: Numer indeksu osoby ocenianej
            grade: Ocena (np. 2-5)
            description: Uzasadnienie oceny
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
        Wczytuje wszystkie oceny z pliku CSV i dodaje je do bazy Neo4j.

        Args:
            csv_path (str): ścieżka do pliku CSV zawierającego kolumny:
                type, grader_id, project_id, graded_id, grade, explanation
        """
        import csv

        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            count = 0


            for row in csv_reader:
                # Pomijamy wiersze z komentarzami lub puste wiersze
                if not row.get('type') or row['type'].strip().startswith('#'):
                    continue
                
                # Pomijamy wiersze bez wymaganych danych
                if not row.get('grader_id') or not row.get('grade'):
                    print(f"Pomijam wiersz z brakującymi danymi: {row}")
                    continue
                
                try:
                    grade_type = row['type'].strip()
                    grader_id = int(row['grader_id'])
                    project_id = int(row['project_id']) if row.get('project_id') and row['project_id'].strip() else None
                    graded_id = int(row['graded_id']) if row.get('graded_id') and row['graded_id'].strip() else None
                    grade = float(row['grade'])
                    explanation = row.get('explanation', '').strip()
                except (ValueError, TypeError) as e:
                    print(f"Błąd konwersji danych w wierszu: {row}. Błąd: {e}")
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
                    print(f"[{count}]  Zapisano ocenę typu '{grade_type}' od {grader_id}")

                except Exception as e:
                    print(f" Błąd przy zapisie oceny typu '{grade_type}' od {grader_id}: {e}")

        print(f"Zakończono! Wczytano {count} ocen z pliku '{csv_path}'")

    def fill_database_no_grades(self, csv_path: str):
        """
        Wypełnij bazę danych studentami i projektami z pliku CSV
        
        Args:
            csv_path: Ścieżka do pliku CSV
        
        Format CSV:
            index,name,surname,github,project_id,project_name,role
        """
        import csv
        
        with self.driver.session() as session:
            # Najpierw wyczyść bazę (opcjonalnie - odkomentuj jeśli chcesz)
            # session.run("MATCH (n) DETACH DELETE n")
            
            with open(csv_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                
                for row in csv_reader:
                    # Utwórz projekt (jeśli nie istnieje)
                    session.run("""
                        MERGE (p:Project {id: $project_id})
                        ON CREATE SET p.name = $project_name
                    """,
                        project_id=int(row['project_id']),
                        project_name=row['project_name']
                    )
                    
                    # Utwórz studenta
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
                    
                    # Utwórz relację belongs_to
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
            
            print("Baza danych została wypełniona pomyślnie!")

    def clear_database(self):
        """
        Wyczyść całą bazę danych (UWAGA: usuwa wszystkie dane!)
        """
        with self.driver.session() as session:
            result = session.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
            deleted_count = result.single()['deleted']
            print(f"Usunięto {deleted_count} węzłów wraz z relacjami")


#test functions for methods
if __name__ == "__main__":   
    retriever = Neo4jRetriever() # initialize retriever

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------GET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    # print(retriever.get_students())

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------SET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    # print(retriever.set_self_grade(grading_person_index = 2003, grade = 4.5, description = "Dobra praca, ale mogę się jeszcze poprawić"))
    # print(retriever.set_teammate_grade(grading_person_index = 2003, graded_person_index = 2001, grade = 3.5, description="Solidna praca, ale wymaga poprawy w niektórych obszarach"))
    # print(retriever.set_leader_grade(grading_person_index = 2003, project_id = 2, grade = 3.5, description="Świetna prowadził pracę zespołu i dostarczył wartościowe wyniki"))
    # print(retriever.set_project_grade(grading_person_index=2003, project_id=2, grade=4.5, description="Projekt został zrealizowany zgodnie z założeniami"))
    # print(retriever.set_project_objectives_grade(grading_person_index=2001, project_id=2, grade=5.0, description="Założenia były jasno określone i realistyczne"))

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------FILL THE BASE---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    # retriever.clear_database()
    # retriever.fill_database_no_grades("src/neo4j_retriever/data_no_grades.csv")
    # retriever.fill_database_with_grades("src/neo4j_retriever/grades.csv")
    retriever.close() # destroy retriever
