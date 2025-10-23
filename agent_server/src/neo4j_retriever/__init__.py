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
            result = session.run("MATCH (s:Student) RETURN s.imie AS imie, s.nazwisko AS nazwisko, s.nr_indeksu AS nr_indeksu")
            return [{"imie": record["imie"], "nazwisko": record["nazwisko"], "nr_indeksu": record["nr_indeksu"]} for record in result]
        
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
                MATCH (student:Student {nr_indeksu: $grading_person_index})
                CREATE (student)-[:WYKONAŁ]->(o:Odpowiedź {
                    typ_pytania: "ocena_własna",
                    ocena: $grade,
                    uzasadnienie: $description
                })-[:DOTYCZY]->(student)
                RETURN student.imie as imie, 
                    student.nazwisko as nazwisko,
                    student.nr_indeksu as nr_indeksu,
                    o.typ_pytania,
                    o.ocena, 
                    o.uzasadnienie
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
                MATCH (autor:Student {nr_indeksu: $grading_person_index}),
                    (oceniany:Student {nr_indeksu: $graded_person_index})
                CREATE (autor)-[:WYKONAŁ]->(o:Odpowiedź {
                    typ_pytania: "ocena_członka",
                    ocena: $grade,
                    uzasadnienie: $description
                })-[:DOTYCZY]->(oceniany)
                RETURN autor.imie as kto_ocenił, 
                    autor.nazwisko as nazwisko_autora,
                    oceniany.imie as kogo_ocenił,
                    oceniany.nazwisko as nazwisko_ocenianego,
                    o.ocena, 
                    o.uzasadnienie
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
        project_id: int,  # ID projektu, którego lidera oceniamy
        grade: float,
        description: str,
    ):
        """
        Zapisz ocenę lidera projektu
        
        Args:
            grading_person_index: Numer indeksu osoby oceniającej
            project_id: ID projektu, którego lidera oceniamy
            grade: Ocena zarządzania (np. 2-5)
            description: Uzasadnienie oceny
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (oceniajacy:Student {nr_indeksu: $grading_person_index})
                MATCH (lider:Student)-[r:NALEŻY_DO]->(projekt:Projekt {id: $project_id})
                WHERE r.rola = "lider"
                CREATE (oceniajacy)-[:WYKONAŁ]->(o:Odpowiedź {
                    typ_pytania: "ocena_zarządzania",
                    ocena: $grade,
                    uzasadnienie: $description
                })-[:DOTYCZY]->(lider)
                RETURN oceniajacy.imie as kto_ocenił,
                    oceniajacy.nazwisko as nazwisko_oceniajacego,
                    lider.imie as lider_imie,
                    lider.nazwisko as lider_nazwisko,
                    lider.nr_indeksu as lider_nr_indeksu,
                    projekt.id as projekt_id,
                    projekt.nazwa as projekt_nazwa,
                    o.ocena,
                    o.uzasadnienie
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
        Zapisz ocenę projektu
        
        Args:
            grading_person_index: Numer indeksu osoby oceniającej
            project_id: ID projektu
            grade: Ocena projektu (np. 2-5)
            description: Uzasadnienie oceny
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {nr_indeksu: $grading_person_index})
                MATCH (projekt:Projekt {id: $project_id})
                CREATE (student)-[:WYKONAŁ]->(o:Odpowiedź {
                    typ_pytania: "ocena_projektu",
                    ocena: $grade,
                    uzasadnienie: $description
                })-[:DOTYCZY]->(projekt)
                RETURN student.imie as kto_ocenił,
                    student.nazwisko as nazwisko_oceniajacego,
                    student.nr_indeksu as nr_indeksu,
                    projekt.id as projekt_id,
                    projekt.nazwa as projekt_nazwa,
                    o.typ_pytania,
                    o.ocena,
                    o.uzasadnienie
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
        Zapisz ocenę założeń projektu
        
        Args:
            grading_person_index: Numer indeksu osoby oceniającej
            project_id: ID projektu
            grade: Ocena założeń projektu (np. 2-5)
            description: Uzasadnienie oceny
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (student:Student {nr_indeksu: $grading_person_index})
                MATCH (projekt:Projekt {id: $project_id})
                CREATE (student)-[:WYKONAŁ]->(o:Odpowiedź {
                    typ_pytania: "ocena_założeń",
                    ocena: $grade,
                    uzasadnienie: $description
                })-[:DOTYCZY]->(projekt)
                RETURN student.imie as kto_ocenił,
                    student.nazwisko as nazwisko_oceniajacego,
                    student.nr_indeksu as nr_indeksu,
                    projekt.id as projekt_id,
                    projekt.nazwa as projekt_nazwa,
                    o.typ_pytania,
                    o.ocena,
                    o.uzasadnienie
            """,
                grading_person_index=grading_person_index,
                project_id=project_id,
                grade=grade,
                description=description
            )
            return result.single()

#test functions for methods
if __name__ == "__main__":   
    retriever = Neo4jRetriever() # initialize retriever

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------GET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    #print(retriever.get_students()) 

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------SET METHODS---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    #print(retriever.set_self_grade(grading_person_index = 2003, grade = 4.5, description = "Dobra praca, ale mogę się jeszcze poprawić"))
    #print(retriever.set_teammate_grade(grading_person_index = 2003, graded_person_index = 2001, grade = 3.5, description="Solidna praca, ale wymaga poprawy w niektórych obszarach"))
    #print(retriever.set_leader_grade(grading_person_index = 2003, project_id = 2, grade = 3.5, description="Świetna prowadził pracę zespołu i dostarczył wartościowe wyniki"))
    #print(retriever.set_project_grade(grading_person_index=2003, project_id=2, grade=4.5, description="Projekt został zrealizowany zgodnie z założeniami"))
    #print(retriever.set_project_objectives_grade(grading_person_index=2001, project_id=2, grade=5.0, description="Założenia były jasno określone i realistyczne"))

#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------FILL THE BASE---------------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# TO DO

    retriever.close() # destroy retriever
