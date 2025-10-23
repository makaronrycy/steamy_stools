from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

#to solve problems with .env path
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

class Neo4jRetriever:
    def __init__(self, uri=None, username=None, password=None):
        self.driver = GraphDatabase.driver(
            uri or os.getenv("NEO4J_URI"),
            auth=(username or os.getenv("NEO4J_USERNAME"), 
                  password or os.getenv("NEO4J_PASSWORD"))
        )

    def get_node_types(self):
        return {"node_types": []}
    
    def get_students(self):
        with self.driver.session() as session:
            result = session.run("MATCH (s:Student) RETURN s.imie AS imie, s.nazwisko AS nazwisko, s.nr_indeksu AS nr_indeksu")
            return [{"imie": record["imie"], "nazwisko": record["nazwisko"], "nr_indeksu": record["nr_indeksu"]} for record in result]
        
    def close(self):
        self.driver.close()
    
    def set_self_grade(
        self, 
        grading_person_id: str,
        grade: float,
        description: str,
    ):
        pass

    def set_teammate_grade(
        self, 
        grading_person_id: str,
        graded_person_id: str,
        grade: float,
        description: str,
    ):
        pass

    def set_leader_grade(
        self, 
        grading_person_id: str,
        project_id: str,
        description: str,
    ):
        pass

if __name__ == "__main__":
    # Inicjalizacja
    retriever = Neo4jRetriever(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="your_password"
    )
    
    try:
        # Samoocena
        retriever.set_self_grade(
            grading_person_id = "",
            grade = "4.5",
            description = "Dobra praca, ale mogę się jeszcze poprawić",
        )
        
        # Ocena kolegi
        retriever.set_teammate_grade(
            grading_person_id = "",
            graded_person_id = "",
            grade = 3.5,
            description="Solidna praca, ale wymaga poprawy w niektórych obszarach",
        )
        
        # Ocena lidera
        retriever.set_leader_grade(
            grading_person_id = "",
            project_id = "",
            description="Świetna prowadził pracę zespołu i dostarczył wartościowe wyniki",
        )
        
        print("Oceny zapisane pomyślnie!")
        
    finally:
        retriever.close()

# if __name__ == "__main__":
       
#     retriever = Neo4jRetriever()
#     students = retriever.get_students()
#     print(students)
#     retriever.close()