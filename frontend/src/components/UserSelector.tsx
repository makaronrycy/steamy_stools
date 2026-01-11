import React, { useEffect, useState } from "react";
import { api } from "../services/api";

type Person = {
    name: string;
    surname: string;
    index: string;
};

type Project = {
    project_id: string;
    project_name: string;
    people: Person[];
};

interface UserSelectorProps {
    onSelect: (userId: string, userName: string) => void;
}

const UserSelector: React.FC<UserSelectorProps> = ({ onSelect }) => {
    const [projects, setProjects] = useState<Project[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchPeople = async () => {
            try {
                const data = await api.getPeople();
                if (Array.isArray(data)) {
                    setProjects(data);
                } else {
                    setError("Nieprawidłowy format danych z serwera.");
                }
            } catch (err) {
                setError("Nie udało się pobrać listy użytkowników.");
            } finally {
                setLoading(false);
            }
        };

        fetchPeople();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full text-white/70">
                Ładowanie listy użytkowników...
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-full text-red-400">
                {error}
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center p-8 w-full max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-white mb-8 drop-shadow-lg">
                Wybierz użytkownika
            </h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                {projects.map((project) => (
                    <div
                        key={project.project_id}
                        className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20 shadow-xl"
                    >
                        <h2 className="text-xl font-semibold text-blue-200 mb-4 border-b border-white/10 pb-2">
                            {project.project_name}
                        </h2>
                        <div className="space-y-2">
                            {project.people.map((person) => (
                                <button
                                    key={person.index}
                                    onClick={() => onSelect(person.index, `${person.name} ${person.surname}`)}
                                    className="w-full text-left px-4 py-3 rounded-lg bg-white/5 hover:bg-blue-500/20 hover:border-blue-400/50 border border-transparent transition-all duration-200 group flex justify-between items-center"
                                >
                                    <span className="text-white group-hover:text-blue-100 font-medium">
                                        {person.name} {person.surname}
                                    </span>
                                    <span className="text-xs text-white/40 bg-white/10 px-2 py-1 rounded">
                                        {person.index}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default UserSelector;
