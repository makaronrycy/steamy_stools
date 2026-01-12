#!/usr/bin/env python3
"""
Generator ocen końcowych studentów na podstawie wszystkich składowych.

WZÓR NA OCENĘ KOŃCOWĄ:
======================
Ocena = w1·Samoocena + w2·ŚrOcenOtrzymanych + w3·OcenaProjektu + w4·OcenaCelów + w5·OcenaGitHub + w6·WspółczynnikZałożeń

Gdzie:
- w1 = 0.10 (samoocena - niska waga, bo subiektywna)
- w2 = 0.25 (średnia ocen otrzymanych od współpracowników - kluczowa)
- w3 = 0.20 (ocena projektu jako całości)
- w4 = 0.15 (ocena realizacji celów projektowych)
- w5 = 0.15 (ocena aktywności na GitHub)
- w6 = 0.15 (współczynnik realizacji założeń projektowych)

WspółczynnikZałożeń obliczany jest jako:
- (liczba założeń ZALICZONYCH / liczba wszystkich założeń) * 5
- Skalowane do zakresu 1-5

Ocena końcowa jest zaokrąglana do najbliższej wartości: 2.0, 3.0, 3.5, 4.0, 4.5, 5.0
(oceny poniżej 2.0 = niezaliczone)
"""

import csv
import os
from datetime import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Ładowanie zmiennych środowiskowych
load_dotenv()

# Konfiguracja wag wzoru
WEIGHTS = {
    'self_assessment': 0.10,        # Samoocena
    'teammate_assessment': 0.25,    # Średnia ocen od współpracowników
    'project_assessment': 0.20,     # Ocena projektu
    'objectives_assessment': 0.15,  # Ocena realizacji celów
    'github_assessment': 0.15,      # Ocena GitHub
    'assumptions_ratio': 0.15       # Współczynnik realizacji założeń
}

# Skala ocen do zaokrąglenia (3.0+ = zdane, 2.0 = niezdane)
GRADE_SCALE = [3.0, 3.5, 4.0, 4.5, 5.0]
FAIL_GRADE = 2.0
PASS_THRESHOLD = 2.75  # Poniżej tego = niezdane (2.0)


class FinalGradeCalculator:
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI', 'neo4j+s://5e28eee4.databases.neo4j.io')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'gwNT2SCurlmO4Do1si4UKz5OMlh06XfVsBJo6VgMt1s')
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Katalog wyjściowy
        self.output_dir = os.path.join(os.path.dirname(__file__), "reports")
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"Łączenie z bazą: {self.uri}")
    
    def __del__(self):
        if hasattr(self, 'driver'):
            self.driver.close()
    
    def _run_query(self, query):
        with self.driver.session() as session:
            result = session.run(query)
            return [record.data() for record in result]
    
    def round_to_grade(self, value):
        """Zaokrągla wartość do najbliższej oceny w skali. Poniżej progu = niezdane (2.0)."""
        if value is None or value < PASS_THRESHOLD:
            return FAIL_GRADE  # Niezdane
        
        closest = min(GRADE_SCALE, key=lambda x: abs(x - value))
        return closest
    
    def get_student_data(self):
        """Pobiera wszystkie dane potrzebne do obliczenia ocen końcowych."""
        
        # Pobierz podstawowe dane studentów z ich ocenami
        query_students = """
        MATCH (s:Student)-[r:belongs_to]->(p:Project)
        OPTIONAL MATCH (s)-[:answered]->(self:Answer {question_type: 'self_assessment'})
        OPTIONAL MATCH (s)-[:answered]->(proj:Answer {question_type: 'project_assessment'})-[:refers_to]->(p)
        OPTIONAL MATCH (s)-[:answered]->(obj:Answer {question_type: 'objectives_assessment'})-[:refers_to]->(p)
        OPTIONAL MATCH (s)-[:answered]->(gh:Answer {question_type: 'github_assessment'})
        OPTIONAL MATCH (s)-[:answered]->(lead:Answer {question_type: 'leadership_assessment'})
        RETURN s.index AS index,
               s.name AS name,
               s.surname AS surname,
               p.id AS project_id,
               p.name AS project_name,
               r.role AS role,
               self.grade AS self_grade,
               proj.grade AS project_grade,
               obj.grade AS objectives_grade,
               gh.grade AS github_grade,
               lead.grade AS leader_grade
        ORDER BY p.id, s.surname
        """
        students_raw = self._run_query(query_students)
        
        # Agreguj dane studentów (mogą być duplikaty przez OPTIONAL MATCH)
        students = {}
        for row in students_raw:
            idx = row['index']
            if idx not in students:
                students[idx] = {
                    'index': idx,
                    'name': row['name'],
                    'surname': row['surname'],
                    'project_id': row['project_id'],
                    'project_name': row['project_name'],
                    'role': row['role'],
                    'self_grade': row['self_grade'],
                    'project_grade': row['project_grade'],
                    'objectives_grade': row['objectives_grade'],
                    'github_grade': row['github_grade'],
                    'leader_grade': row['leader_grade']
                }
            else:
                # Aktualizuj jeśli mamy lepsze dane
                for key in ['self_grade', 'project_grade', 'objectives_grade', 'github_grade', 'leader_grade']:
                    if row[key] is not None and students[idx][key] is None:
                        students[idx][key] = row[key]
        
        # Pobierz średnie oceny otrzymane od współpracowników
        query_teammate_received = """
        MATCH (s:Student)<-[:refers_to]-(a:Answer {question_type: 'teammate_assessment'})
        RETURN s.index AS index, AVG(a.grade) AS avg_teammate_grade, COUNT(a) AS teammate_count
        """
        teammate_data = self._run_query(query_teammate_received)
        teammate_grades = {d['index']: d['avg_teammate_grade'] for d in teammate_data}
        
        # Pobierz współczynnik realizacji założeń dla każdego projektu
        query_assumptions = """
        MATCH (p:Project)-[:has_assumption]->(a:Assumption)
        WITH p.id AS project_id, 
             COUNT(a) AS total_assumptions,
             SUM(CASE WHEN a.system_accepted = true THEN 1 ELSE 0 END) AS passed_assumptions
        RETURN project_id, 
               total_assumptions, 
               passed_assumptions,
               CASE WHEN total_assumptions > 0 
                    THEN toFloat(passed_assumptions) / total_assumptions 
                    ELSE 0 
               END AS pass_ratio
        """
        assumptions_data = self._run_query(query_assumptions)
        assumptions_ratio = {d['project_id']: d for d in assumptions_data}
        
        # Dodaj brakujące dane do studentów
        for idx, student in students.items():
            student['teammate_grade'] = teammate_grades.get(idx)
            proj_assumptions = assumptions_ratio.get(student['project_id'], {})
            student['assumptions_passed'] = proj_assumptions.get('passed_assumptions', 0)
            student['assumptions_total'] = proj_assumptions.get('total_assumptions', 0)
            student['assumptions_ratio'] = proj_assumptions.get('pass_ratio', 0)
            # Przelicz ratio na skalę 1-5 (0% = 1, 100% = 5)
            student['assumptions_grade'] = 1 + student['assumptions_ratio'] * 4
        
        return list(students.values())
    
    def calculate_final_grade(self, student):
        """Oblicza ocenę końcową dla studenta na podstawie wzoru."""
        
        components = {
            'self_assessment': student.get('self_grade'),
            'teammate_assessment': student.get('teammate_grade'),
            'project_assessment': student.get('project_grade'),
            'objectives_assessment': student.get('objectives_grade'),
            'github_assessment': student.get('github_grade'),
            'assumptions_ratio': student.get('assumptions_grade')
        }
        
        # Oblicz ważoną sumę
        weighted_sum = 0
        total_weight = 0
        missing_components = []
        
        for component, value in components.items():
            weight = WEIGHTS[component]
            if value is not None:
                weighted_sum += weight * value
                total_weight += weight
            else:
                missing_components.append(component)
        
        # Normalizuj jeśli brakuje niektórych składowych
        if total_weight > 0:
            raw_grade = weighted_sum / total_weight * sum(WEIGHTS.values())
        else:
            raw_grade = 2.0  # Brak danych = minimalna ocena
        
        # Zaokrąglij do najbliższej oceny w skali
        final_grade = self.round_to_grade(raw_grade)
        
        return {
            'raw_grade': round(raw_grade, 3),
            'final_grade': final_grade,
            'missing_components': missing_components,
            'components': components
        }
    
    def generate_report(self):
        """Generuje raport z ocenami końcowymi."""
        
        print("=" * 70)
        print("KALKULATOR OCEN KOŃCOWYCH")
        print(f"Timestamp: {self.timestamp}")
        print("=" * 70)
        print()
        print("WZÓR NA OCENĘ KOŃCOWĄ:")
        print("-" * 70)
        print("Ocena = w1·Samoocena + w2·ŚrOcenWspółprac. + w3·OcenaProjektu")
        print("      + w4·OcenaCelów + w5·OcenaGitHub + w6·WspółczynnikZałożeń")
        print()
        print("WAGI:")
        for component, weight in WEIGHTS.items():
            print(f"  {component}: {weight:.0%}")
        print("-" * 70)
        print()
        
        # Pobierz dane studentów
        print("Pobieranie danych z bazy...")
        students = self.get_student_data()
        print(f"Znaleziono {len(students)} studentów")
        print()
        
        # Oblicz oceny końcowe
        results = []
        for student in students:
            grade_result = self.calculate_final_grade(student)
            results.append({
                **student,
                **grade_result
            })
        
        # Zapisz do CSV
        filename = f"OCENY_KONCOWE_{self.timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        headers = [
            "Indeks", "Imię", "Nazwisko", "Projekt", "Rola",
            "Samoocena", "Śr. Ocen Współprac.", "Ocena Projektu", 
            "Ocena Celów", "Ocena GitHub", "Wsp. Założeń (1-5)",
            "Założenia (zaliczone/wszystkie)", "Ocena Surowa", "OCENA KOŃCOWA",
            "Brakujące Składowe"
        ]
        
        rows = []
        for r in results:
            rows.append([
                r['index'],
                r['name'],
                r['surname'],
                r['project_name'],
                r['role'],
                r['components']['self_assessment'],
                round(r['components']['teammate_assessment'], 2) if r['components']['teammate_assessment'] else None,
                r['components']['project_assessment'],
                r['components']['objectives_assessment'],
                r['components']['github_assessment'],
                round(r['components']['assumptions_ratio'], 2) if r['components']['assumptions_ratio'] else None,
                f"{r['assumptions_passed']}/{r['assumptions_total']}",
                r['raw_grade'],
                r['final_grade'],
                ", ".join(r['missing_components']) if r['missing_components'] else ""
            ])
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        
        print(f"✓ Zapisano: {filepath}")
        print()
        
        # Wyświetl podsumowanie
        print("=" * 70)
        print("PODSUMOWANIE OCEN KOŃCOWYCH:")
        print("=" * 70)
        print(f"{'Indeks':<10} {'Imię Nazwisko':<25} {'Projekt':<15} {'Surowa':<8} {'KOŃCOWA':<8}")
        print("-" * 70)
        for r in results:
            print(f"{r['index']:<10} {r['name'] + ' ' + r['surname']:<25} {r['project_name'][:15]:<15} {r['raw_grade']:<8.2f} {r['final_grade']:<8.1f}")
        print("-" * 70)
        
        # Statystyki
        final_grades = [r['final_grade'] for r in results]
        raw_grades = [r['raw_grade'] for r in results]
        print()
        print(f"Średnia ocena surowa:   {sum(raw_grades)/len(raw_grades):.2f}")
        print(f"Średnia ocena końcowa:  {sum(final_grades)/len(final_grades):.2f}")
        print(f"Najwyższa ocena:        {max(final_grades):.1f}")
        print(f"Najniższa ocena:        {min(final_grades):.1f}")
        print()
        
        # Zapisz również wzór do osobnego pliku
        self._save_formula_documentation()
        
        return filepath
    
    def _save_formula_documentation(self):
        """Zapisuje dokumentację wzoru do pliku tekstowego."""
        
        doc_filename = f"WZOR_OCENY_{self.timestamp}.txt"
        doc_filepath = os.path.join(self.output_dir, doc_filename)
        
        doc_content = """
================================================================================
                        WZÓR NA OCENĘ KOŃCOWĄ STUDENTA
================================================================================

FORMUŁA:
--------
Ocena = w1·Samoocena + w2·ŚrOcenWspółpracowników + w3·OcenaProjektu 
      + w4·OcenaCelów + w5·OcenaGitHub + w6·WspółczynnikZałożeń

WAGI SKŁADOWYCH:
----------------
"""
        for component, weight in WEIGHTS.items():
            doc_content += f"  {component}: {weight:.0%} ({weight})\n"
        
        doc_content += """
OPIS SKŁADOWYCH:
----------------
1. Samoocena (self_assessment) - 10%
   Subiektywna ocena własnej pracy przez studenta.
   Niska waga ze względu na subiektywność.

2. Średnia ocen od współpracowników (teammate_assessment) - 25%
   Średnia ocen wystawionych studentowi przez innych członków zespołu.
   Najwyższa waga - kluczowy wskaźnik współpracy w zespole.

3. Ocena projektu (project_assessment) - 20%
   Ocena jakości całego projektu wystawiona przez studenta.
   Pośrednio odzwierciedla wkład w projekt.

4. Ocena realizacji celów (objectives_assessment) - 15%
   Ocena stopnia realizacji celów projektowych.

5. Ocena aktywności GitHub (github_assessment) - 15%
   Ocena regularności i jakości commitów na GitHub.

6. Współczynnik realizacji założeń (assumptions_ratio) - 15%
   Obliczany jako: (założenia_zaliczone / założenia_ogółem) * 4 + 1
   Skalowany do zakresu 1-5.
   Wspólny dla całego zespołu projektowego.

ZAOKRĄGLANIE:
-------------
Ocena surowa jest zaokrąglana do najbliższej wartości w skali:
3.0, 3.5, 4.0, 4.5, 5.0 (oceny zaliczające)

PRÓG ZALICZENIA: 2.75
- Ocena surowa >= 2.75 -> zaokrąglenie do skali 3.0-5.0
- Ocena surowa < 2.75 -> NIEZDANE (2.0)

OBSŁUGA BRAKUJĄCYCH DANYCH:
---------------------------
Jeśli brakuje niektórych składowych, wzór jest normalizowany:
- Wagi dostępnych składowych są skalowane tak, by sumowały się do 1
- Brakujące składowe są raportowane w kolumnie "Brakujące Składowe"

================================================================================
"""
        
        with open(doc_filepath, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"✓ Dokumentacja wzoru: {doc_filepath}")


if __name__ == "__main__":
    calculator = FinalGradeCalculator()
    calculator.generate_report()
    print()
    print("=" * 70)
    print("ZAKOŃCZONO!")
    print("=" * 70)
