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

        
# if __name__ == "__main__":
       
#     retriever = Neo4jRetriever()
#     students = retriever.get_students()
#     print(students)
#     retriever.close()
