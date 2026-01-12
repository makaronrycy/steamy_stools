#!/usr/bin/env python3
"""
Skrypt generujący kompleksowe raporty CSV z bazy Neo4j.
Prezentuje wszystkie dane i relacje zawarte w bazie danych systemu ocen studenckich.
"""

import csv
import os
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv


class Neo4jReportGenerator:
    """Generator raportów CSV z bazy Neo4j."""
    
    def __init__(self, uri: str, username: str, password: str, database: str = "neo4j"):
        """
        Inicjalizuje generator raportów CSV z bazy Neo4j.
        
        Tworzy połączenie z bazą danych i przygotowuje katalog wyjściowy
        dla generowanych raportów.
        
        Args:
            uri (str): URI połączenia z bazą Neo4j.
            username (str): Nazwa użytkownika bazy danych.
            password (str): Hasło do bazy danych.
            database (str): Nazwa bazy danych. Domyślnie "neo4j".
        
        Attributes:
            driver: Sterownik Neo4j do wykonywania zapytań.
            database (str): Nazwa bazy danych.
            timestamp (str): Znacznik czasu w formacie YYYYMMDD_HHMMSS.
            reports_dir (str): Ścieżka do katalogu z raportami.
        """
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.database = database
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def close(self):
        """Zamyka połączenie z bazą Neo4j."""
        self.driver.close()
    
    def _run_query(self, query: str):
        """Wykonuje zapytanie Cypher i zwraca wyniki."""
        with self.driver.session(database=self.database) as session:
            result = session.run(query)
            return [record.data() for record in result]
    
    def _save_csv(self, filename: str, headers: list, rows: list):
        """Zapisuje dane do pliku CSV."""
        filepath = os.path.join(self.reports_dir, f"{filename}_{self.timestamp}.csv")
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f"  ✓ Zapisano: {filepath}")
        return filepath
    
    # ========== RAPORTY WĘZŁÓW ==========
    
    def report_01_students(self):
        """Raport 1: Lista wszystkich studentów."""
        print("\n[1/14] Generowanie raportu: Studenci...")
        query = """
        MATCH (s:Student)-[r:belongs_to]->(p:Project)
        RETURN s.index AS student_index, 
               s.name AS name,
               s.surname AS surname,
               p.id AS project_id,
               p.name AS project_name,
               CASE WHEN r.role = 'leader' THEN 'TAK' ELSE 'NIE' END AS is_leader
        ORDER BY p.id, s.index
        """
        data = self._run_query(query)
        headers = ["Indeks Studenta", "Imię", "Nazwisko", "ID Projektu", "Nazwa Projektu", "Lider?"]
        rows = [[d['student_index'], d['name'], d['surname'], d['project_id'], d['project_name'], d['is_leader']] for d in data]
        return self._save_csv("01_studenci", headers, rows)
    
    def report_02_projects(self):
        """Raport 2: Lista projektów."""
        print("[2/14] Generowanie raportu: Projekty...")
        query = """
        MATCH (p:Project)
        OPTIONAL MATCH (leader:Student)-[lr:belongs_to {role: 'leader'}]->(p)
        OPTIONAL MATCH (s:Student)-[:belongs_to]->(p)
        WITH p, leader, COUNT(DISTINCT s) AS member_count
        OPTIONAL MATCH (p)-[:has_assumption]->(a:Assumption)
        WITH p, leader, member_count, 
             COUNT(a) AS total_assumptions,
             SUM(CASE WHEN a.system_accepted = true THEN 1 ELSE 0 END) AS accepted_assumptions
        RETURN p.id AS project_id,
               p.name AS project_name,
               leader.index AS leader_index,
               leader.name AS leader_name,
               leader.surname AS leader_surname,
               member_count,
               total_assumptions,
               accepted_assumptions,
               total_assumptions - accepted_assumptions AS rejected_assumptions
        ORDER BY p.id
        """
        data = self._run_query(query)
        headers = ["ID Projektu", "Nazwa Projektu", "Indeks Lidera", "Imię Lidera", "Nazwisko Lidera",
                   "Liczba Członków", "Założenia Razem", "Założenia Zaliczone", "Założenia Niezaliczone"]
        rows = [[d['project_id'], d['project_name'], d['leader_index'], d['leader_name'], d['leader_surname'],
                 d['member_count'], d['total_assumptions'], d['accepted_assumptions'], 
                 d['rejected_assumptions']] for d in data]
        return self._save_csv("02_projekty", headers, rows)
    
    def report_03_assumptions(self):
        """Raport 3: Lista założeń projektowych."""
        print("[3/14] Generowanie raportu: Założenia projektowe...")
        query = """
        MATCH (p:Project)-[:has_assumption]->(a:Assumption)
        RETURN p.id AS project_id,
               p.name AS project_name,
               a.description AS description,
               CASE WHEN a.system_accepted = true THEN 'ZALICZONE' ELSE 'NIEZALICZONE' END AS status
        ORDER BY p.id
        """
        data = self._run_query(query)
        headers = ["ID Projektu", "Nazwa Projektu", "Opis Założenia", "Status"]
        rows = [[d['project_id'], d['project_name'], d['description'], d['status']] for d in data]
        return self._save_csv("03_zalozenia", headers, rows)
    
    # ========== RAPORTY OCEN ==========
    
    def report_04_self_assessments(self):
        """Raport 4: Samooceny studentów."""
        print("[4/14] Generowanie raportu: Samooceny...")
        query = """
        MATCH (s:Student)-[:answered]->(ans:Answer)
        WHERE ans.question_type = 'self_assessment'
        MATCH (s)-[:belongs_to]->(p:Project)
        RETURN s.index AS student_index,
               s.name AS name,
               s.surname AS surname,
               p.id AS project_id,
               p.name AS project_name,
               ans.grade AS grade,
               ans.explanation AS explanation
        ORDER BY p.id, s.index
        """
        data = self._run_query(query)
        headers = ["Indeks Studenta", "Imię", "Nazwisko", "ID Projektu", "Projekt", "Ocena", "Uzasadnienie"]
        rows = [[d['student_index'], d['name'], d['surname'], d['project_id'], d['project_name'],
                 d['grade'], d['explanation']] for d in data]
        return self._save_csv("04_samooceny", headers, rows)
    
    def report_05_project_assessments(self):
        """Raport 5: Oceny projektów."""
        print("[5/14] Generowanie raportu: Oceny projektów...")
        query = """
        MATCH (s:Student)-[:answered]->(ans:Answer)-[:refers_to]->(p:Project)
        WHERE ans.question_type = 'project_assessment'
        MATCH (s)-[:belongs_to]->(student_project:Project)
        RETURN s.index AS grader_index,
               s.name AS grader_name,
               s.surname AS grader_surname,
               student_project.id AS grader_project_id,
               p.id AS graded_project_id,
               p.name AS graded_project_name,
               ans.grade AS grade,
               ans.explanation AS explanation
        ORDER BY s.index, p.id
        """
        data = self._run_query(query)
        headers = ["Indeks Oceniającego", "Imię", "Nazwisko", "Projekt Oceniającego", 
                   "ID Ocenianego Projektu", "Oceniany Projekt", "Ocena", "Uzasadnienie"]
        rows = [[d['grader_index'], d['grader_name'], d['grader_surname'], d['grader_project_id'],
                 d['graded_project_id'], d['graded_project_name'], d['grade'], d['explanation']] for d in data]
        return self._save_csv("05_oceny_projektow", headers, rows)
    
    def report_06_teammate_assessments(self):
        """Raport 6: Oceny współpracowników."""
        print("[6/14] Generowanie raportu: Oceny współpracowników...")
        query = """
        MATCH (grader:Student)-[:answered]->(ans:Answer)-[:refers_to]->(graded:Student)
        WHERE ans.question_type = 'teammate_assessment'
        MATCH (grader)-[:belongs_to]->(p:Project)
        RETURN grader.index AS grader_index,
               grader.name AS grader_name,
               grader.surname AS grader_surname,
               graded.index AS graded_index,
               graded.name AS graded_name,
               graded.surname AS graded_surname,
               p.id AS project_id,
               p.name AS project_name,
               ans.grade AS grade,
               ans.explanation AS explanation
        ORDER BY p.id, grader.index, graded.index
        """
        data = self._run_query(query)
        headers = ["Indeks Oceniającego", "Imię Oceniającego", "Nazwisko Oceniającego",
                   "Indeks Ocenianego", "Imię Ocenianego", "Nazwisko Ocenianego",
                   "ID Projektu", "Projekt", "Ocena", "Uzasadnienie"]
        rows = [[d['grader_index'], d['grader_name'], d['grader_surname'],
                 d['graded_index'], d['graded_name'], d['graded_surname'],
                 d['project_id'], d['project_name'], d['grade'], d['explanation']] for d in data]
        return self._save_csv("06_oceny_wspolpracownikow", headers, rows)
    
    def report_07_leadership_assessments(self):
        """Raport 7: Oceny liderów."""
        print("[7/14] Generowanie raportu: Oceny liderów...")
        query = """
        MATCH (s:Student)-[:answered]->(ans:Answer)
        WHERE ans.question_type = 'leadership_assessment'
        MATCH (s)-[:belongs_to]->(p:Project)
        OPTIONAL MATCH (leader:Student)-[lr:belongs_to {role: 'leader'}]->(p)
        RETURN s.index AS grader_index,
               s.name AS grader_name,
               s.surname AS grader_surname,
               p.id AS project_id,
               p.name AS project_name,
               leader.index AS leader_index,
               leader.name AS leader_name,
               leader.surname AS leader_surname,
               ans.grade AS grade,
               ans.explanation AS explanation
        ORDER BY p.id, s.index
        """
        data = self._run_query(query)
        headers = ["Indeks Oceniającego", "Imię Oceniającego", "Nazwisko Oceniającego",
                   "ID Projektu", "Projekt", "Indeks Lidera", "Imię Lidera", "Nazwisko Lidera",
                   "Ocena", "Uzasadnienie"]
        rows = [[d['grader_index'], d['grader_name'], d['grader_surname'],
                 d['project_id'], d['project_name'], d['leader_index'], d['leader_name'], d['leader_surname'],
                 d['grade'], d['explanation']] for d in data]
        return self._save_csv("07_oceny_liderow", headers, rows)
    
    def report_08_objectives_assessments(self):
        """Raport 8: Oceny realizacji celów."""
        print("[8/14] Generowanie raportu: Oceny realizacji celów...")
        query = """
        MATCH (s:Student)-[:answered]->(ans:Answer)
        WHERE ans.question_type = 'objectives_assessment'
        MATCH (s)-[:belongs_to]->(p:Project)
        RETURN s.index AS student_index,
               s.name AS name,
               s.surname AS surname,
               p.id AS project_id,
               p.name AS project_name,
               ans.grade AS grade,
               ans.explanation AS explanation
        ORDER BY p.id, s.index
        """
        data = self._run_query(query)
        headers = ["Indeks Studenta", "Imię", "Nazwisko", "ID Projektu", "Projekt", "Ocena", "Uzasadnienie"]
        rows = [[d['student_index'], d['name'], d['surname'], d['project_id'], d['project_name'],
                 d['grade'], d['explanation']] for d in data]
        return self._save_csv("08_oceny_realizacji_celow", headers, rows)
    
    def report_09_github_assessments(self):
        """Raport 9: Oceny GitHub."""
        print("[9/14] Generowanie raportu: Oceny GitHub...")
        query = """
        MATCH (s:Student)-[:answered]->(ans:Answer)
        WHERE ans.question_type = 'github_assessment'
        MATCH (s)-[:belongs_to]->(p:Project)
        RETURN s.index AS student_index,
               s.name AS name,
               s.surname AS surname,
               p.id AS project_id,
               p.name AS project_name,
               ans.grade AS grade,
               ans.explanation AS explanation
        ORDER BY p.id, s.index
        """
        data = self._run_query(query)
        headers = ["Indeks Studenta", "Imię", "Nazwisko", "ID Projektu", "Projekt", "Ocena", "Uzasadnienie"]
        rows = [[d['student_index'], d['name'], d['surname'], d['project_id'], d['project_name'],
                 d['grade'], d['explanation']] for d in data]
        return self._save_csv("09_oceny_github", headers, rows)
    
    def report_10_assumption_evaluations(self):
        """Raport 10: Ewaluacje założeń przez studentów."""
        print("[10/14] Generowanie raportu: Ewaluacje założeń...")
        query = """
        MATCH (s:Student)-[:evaluated]->(ae:AssumptionEvaluation)-[:refers_to]->(a:Assumption)
        MATCH (a)<-[:has_assumption]-(p:Project)
        RETURN s.index AS student_index,
               s.name AS name,
               s.surname AS surname,
               p.id AS project_id,
               p.name AS project_name,
               a.description AS assumption_description,
               ae.grade AS grade,
               ae.explanation AS explanation
        ORDER BY p.id, s.index
        """
        data = self._run_query(query)
        headers = ["Indeks Studenta", "Imię", "Nazwisko", "ID Projektu", "Projekt", 
                   "Opis Założenia", "Ocena", "Uzasadnienie"]
        rows = [[d['student_index'], d['name'], d['surname'], d['project_id'], d['project_name'],
                 d['assumption_description'], d['grade'], d['explanation']] for d in data]
        return self._save_csv("10_ewaluacje_zalozen", headers, rows)
    
    # ========== RAPORTY PODSUMOWUJĄCE ==========
    
    def report_11_student_grades_summary(self):
        """Raport 11: Podsumowanie ocen studentów."""
        print("[11/14] Generowanie raportu: Podsumowanie ocen studentów...")
        query = """
        MATCH (s:Student)-[:belongs_to]->(p:Project)
        
        // Samoocena
        OPTIONAL MATCH (s)-[:answered]->(self_ans:Answer)
        WHERE self_ans.question_type = 'self_assessment'
        
        // Ocena realizacji celów
        OPTIONAL MATCH (s)-[:answered]->(obj_ans:Answer)
        WHERE obj_ans.question_type = 'objectives_assessment'
        
        // Ocena lidera
        OPTIONAL MATCH (s)-[:answered]->(lead_ans:Answer)
        WHERE lead_ans.question_type = 'leadership_assessment'
        
        // GitHub
        OPTIONAL MATCH (s)-[:answered]->(github_ans:Answer)
        WHERE github_ans.question_type = 'github_assessment'
        
        // Średnia ocen od współpracowników
        OPTIONAL MATCH (other:Student)-[:answered]->(team_ans:Answer)-[:refers_to]->(s)
        WHERE team_ans.question_type = 'teammate_assessment'
        
        // Średnia ocen wystawionych współpracownikom
        OPTIONAL MATCH (s)-[:answered]->(given_ans:Answer)-[:refers_to]->(:Student)
        WHERE given_ans.question_type = 'teammate_assessment'
        
        // Ewaluacje założeń
        OPTIONAL MATCH (s)-[:evaluated]->(ae:AssumptionEvaluation)
        
        WITH s, p, self_ans, obj_ans, lead_ans, github_ans,
             AVG(team_ans.grade) AS avg_received_teammate_grade,
             COUNT(DISTINCT team_ans) AS received_teammate_count,
             AVG(given_ans.grade) AS avg_given_teammate_grade,
             COUNT(DISTINCT given_ans) AS given_teammate_count,
             AVG(ae.grade) AS avg_assumption_eval,
             COUNT(DISTINCT ae) AS assumption_eval_count
        
        RETURN s.index AS student_index,
               s.name AS name,
               s.surname AS surname,
               p.id AS project_id,
               p.name AS project_name,
               self_ans.grade AS self_assessment,
               obj_ans.grade AS objectives_assessment,
               lead_ans.grade AS leadership_assessment,
               github_ans.grade AS github_assessment,
               ROUND(avg_received_teammate_grade * 100) / 100 AS avg_teammate_received,
               received_teammate_count AS teammate_grades_received,
               ROUND(avg_given_teammate_grade * 100) / 100 AS avg_teammate_given,
               given_teammate_count AS teammate_grades_given,
               ROUND(avg_assumption_eval * 100) / 100 AS avg_assumption_evaluation,
               assumption_eval_count AS assumption_evaluations_count
        ORDER BY p.id, s.index
        """
        data = self._run_query(query)
        headers = ["Indeks Studenta", "Imię", "Nazwisko", "ID Projektu", "Projekt", 
                   "Samoocena", "Ocena Celów", "Ocena Lidera", "Ocena GitHub",
                   "Śr. Ocen Otrzymanych", "Ile Otrzymał", "Śr. Ocen Wystawionych", "Ile Wystawił",
                   "Śr. Ewaluacji Założeń", "Ile Ewaluacji"]
        rows = [[d['student_index'], d['name'], d['surname'], d['project_id'], d['project_name'],
                 d['self_assessment'], d['objectives_assessment'], d['leadership_assessment'], d['github_assessment'],
                 d['avg_teammate_received'], d['teammate_grades_received'],
                 d['avg_teammate_given'], d['teammate_grades_given'],
                 d['avg_assumption_evaluation'], d['assumption_evaluations_count']] for d in data]
        return self._save_csv("11_podsumowanie_ocen_studentow", headers, rows)
    
    def report_12_assumptions_summary(self):
        """Raport 12: Podsumowanie założeń projektowych."""
        print("[12/14] Generowanie raportu: Podsumowanie założeń...")
        query = """
        MATCH (p:Project)-[:has_assumption]->(a:Assumption)
        OPTIONAL MATCH (ae:AssumptionEvaluation)-[:refers_to]->(a)
        WITH p, a, 
             COUNT(ae) AS eval_count,
             AVG(ae.grade) AS avg_grade,
             COLLECT(ae.grade) AS all_grades
        RETURN p.id AS project_id,
               p.name AS project_name,
               a.description AS description,
               CASE WHEN a.system_accepted = true THEN 'ZALICZONE' ELSE 'NIEZALICZONE' END AS system_status,
               eval_count AS evaluations_count,
               ROUND(avg_grade * 100) / 100 AS avg_student_grade,
               SIZE([g IN all_grades WHERE g >= 2]) AS positive_evals,
               SIZE([g IN all_grades WHERE g < 2]) AS negative_evals
        ORDER BY p.id
        """
        data = self._run_query(query)
        headers = ["ID Projektu", "Projekt", "Opis Założenia", 
                   "Status Systemu", "Liczba Ewaluacji", "Śr. Ocena Studentów", 
                   "Oceny Pozytywne (≥2)", "Oceny Negatywne (<2)"]
        rows = [[d['project_id'], d['project_name'], d['description'],
                 d['system_status'], d['evaluations_count'], d['avg_student_grade'],
                 d['positive_evals'], d['negative_evals']] for d in data]
        return self._save_csv("12_podsumowanie_zalozen", headers, rows)
    
    def report_13_all_relationships(self):
        """Raport 13: Wszystkie relacje w bazie."""
        print("[13/14] Generowanie raportu: Wszystkie relacje...")
        query = """
        MATCH (a)-[r]->(b)
        RETURN labels(a)[0] AS source_type,
               CASE labels(a)[0]
                   WHEN 'Student' THEN a.name + ' ' + a.surname + ' (' + a.index + ')'
                   WHEN 'Project' THEN a.name + ' (ID:' + a.id + ')'
                   WHEN 'Assumption' THEN LEFT(a.description, 60) + '...'
                   WHEN 'Answer' THEN a.question_type + ' (ocena: ' + toString(a.grade) + ')'
                   WHEN 'AssumptionEvaluation' THEN 'Ewaluacja (ocena: ' + toString(a.grade) + ')'
                   ELSE COALESCE(a.name, a.description, 'N/A')
               END AS source_info,
               type(r) AS relationship_type,
               CASE WHEN r.role IS NOT NULL THEN r.role ELSE '' END AS rel_role,
               labels(b)[0] AS target_type,
               CASE labels(b)[0]
                   WHEN 'Student' THEN b.name + ' ' + b.surname + ' (' + b.index + ')'
                   WHEN 'Project' THEN b.name + ' (ID:' + b.id + ')'
                   WHEN 'Assumption' THEN LEFT(b.description, 60) + '...'
                   WHEN 'Answer' THEN b.question_type + ' (ocena: ' + toString(b.grade) + ')'
                   WHEN 'AssumptionEvaluation' THEN 'Ewaluacja (ocena: ' + toString(b.grade) + ')'
                   ELSE COALESCE(b.name, b.description, 'N/A')
               END AS target_info
        ORDER BY source_type, relationship_type, target_type
        """
        data = self._run_query(query)
        headers = ["Typ Źródła", "Źródło", "Relacja", "Rola", "Typ Celu", "Cel"]
        rows = [[d['source_type'], d['source_info'], d['relationship_type'], 
                 d['rel_role'], d['target_type'], d['target_info']] for d in data]
        return self._save_csv("13_wszystkie_relacje", headers, rows)
    
    def report_14_database_statistics(self):
        """Raport 14: Statystyki bazy danych."""
        print("[14/14] Generowanie raportu: Statystyki bazy...")
        
        # Liczba węzłów według typu
        nodes_query = """
        MATCH (n)
        RETURN labels(n)[0] AS label, COUNT(n) AS count
        ORDER BY label
        """
        nodes_data = self._run_query(nodes_query)
        
        # Liczba relacji według typu
        rels_query = """
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, COUNT(r) AS count
        ORDER BY rel_type
        """
        rels_data = self._run_query(rels_query)
        
        headers = ["Kategoria", "Typ", "Liczba"]
        rows = []
        
        total_nodes = 0
        for d in nodes_data:
            rows.append(["Węzły", d['label'], d['count']])
            total_nodes += d['count']
        
        total_rels = 0
        for d in rels_data:
            rows.append(["Relacje", d['rel_type'], d['count']])
            total_rels += d['count']
        
        rows.append(["SUMA", "Węzły", total_nodes])
        rows.append(["SUMA", "Relacje", total_rels])
        
        return self._save_csv("14_statystyki_bazy", headers, rows)
    
    def generate_all_reports(self):
        """Generuje wszystkie raporty."""
        print("=" * 60)
        print("GENERATOR RAPORTÓW Z BAZY NEO4J")
        print(f"Timestamp: {self.timestamp}")
        print("=" * 60)
        
        reports = []
        
        # Węzły
        reports.append(self.report_01_students())
        reports.append(self.report_02_projects())
        reports.append(self.report_03_assumptions())
        
        # Oceny
        reports.append(self.report_04_self_assessments())
        reports.append(self.report_05_project_assessments())
        reports.append(self.report_06_teammate_assessments())
        reports.append(self.report_07_leadership_assessments())
        reports.append(self.report_08_objectives_assessments())
        reports.append(self.report_09_github_assessments())
        reports.append(self.report_10_assumption_evaluations())
        
        # Podsumowania
        reports.append(self.report_11_student_grades_summary())
        reports.append(self.report_12_assumptions_summary())
        reports.append(self.report_13_all_relationships())
        reports.append(self.report_14_database_statistics())
        
        print("\n" + "=" * 60)
        print(f"ZAKOŃCZONO! Wygenerowano {len(reports)} raportów.")
        print(f"Pliki zapisano w: {self.reports_dir}")
        print("=" * 60)
        
        return reports


def main():
    """Główna funkcja uruchamiająca generator raportów."""
    
    # Wczytaj zmienne środowiskowe
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Spróbuj wczytać z .env w katalogu agent_server
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    # Konfiguracja połączenia
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://5e28eee4.databases.neo4j.io")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "gwNT2SCurlmO4Do1si4UKz5OMlh06XfVsBJo6VgMt1s")
    NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
    
    print(f"Łączenie z bazą: {NEO4J_URI}")
    
    generator = Neo4jReportGenerator(
        uri=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE
    )
    
    try:
        generator.generate_all_reports()
    finally:
        generator.close()


if __name__ == "__main__":
    main()
