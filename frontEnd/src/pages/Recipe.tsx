import { useState, useEffect } from "react";
import { backendServer } from "../CONSTANTS";
import styles from "../styles/Recipes.module.css"

async function fetchRecipesFromAPI(allergens: string[]) {
    try {
        const response = await fetch(`http://${backendServer}:5000/api/recipes`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ allergens })
        })
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`)
        }
        const data = await response.json()
        console.log('API response:', data)
        return Array.isArray(data) ? data : [data]
    } catch (error) {
        console.error('Failed to fetch recipes:', error)
        return []
    }
}

export default function Recipe() {
    const [recipes, setRecipes] = useState<string[] | null>([]);
    const [allergens] = useState<string[]>(() => {
        const saved = localStorage.getItem('allergens');
        return saved ? JSON.parse(saved) : [];
    });

    useEffect(() => {
        fetchRecipesFromAPI(allergens).then(data => setRecipes(data));
    }, [allergens])

    return (
        <div>
            <h1 className={styles.pageName}>Recipes</h1>
            <h2>Your Allergens:</h2>
            {allergens.length > 0 ? (
                <ul>
                    {allergens.map(allergen => (
                        <li key={allergen}>{allergen}</li>
                    ))}
                </ul>
            ) : (
                <p>No allergens selected. Go to Settings to add them.</p>
            )}

            <h2>Recipes:</h2>
            {recipes && recipes.length > 0 ? (
                <div>
                    {recipes.map((recipe, index) => (
                        <div key={index} style={{ border: '1px solid #ccc', padding: '10px', margin: '10px 0' }}>
                            <pre>{JSON.stringify(recipe, null, 2)}</pre>
                        </div>
                    ))}
                </div>
            ) : (
                <p>No recipes found.</p>
            )}
        </div>
    )
}