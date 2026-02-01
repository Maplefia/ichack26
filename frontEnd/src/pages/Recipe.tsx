// Recipe.tsx
import { useState, useEffect } from "react";
import { backendServer } from "../CONSTANTS"; // Assuming backendServer is like "localhost:5001"
import styles from "../styles/Recipes.module.css";

// Define the interface for a single Recipe object
interface Recipe {
    name: string;
    ingredients: string[];
}

function RecipeCard({ recipe }: { recipe: Recipe }) {
    return (
        <div className={styles.recipeCard}>
            <h3 className={styles.recipeName}>{recipe.name}</h3>
            <h4 className={styles.ingredientsTitle}>Key Ingredients:</h4>
            <ul className={styles.ingredientsList}>
                {recipe.ingredients.map((ingredient, ingIndex) => (
                    <li key={ingIndex}>{ingredient}</li>
                ))}
            </ul>
        </div>
    )
}

// Function to fetch recipes from the backend API
async function fetchRecipesFromAPI(allergens: string[]): Promise<Recipe[]> {
    try {
        const response = await fetch(`http://${backendServer}/api/recipes`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ allergens })
        });

        if (!response.ok) {
            // Attempt to read a more detailed error message from the backend if available
            const errorBody = await response.json().catch(() => ({ message: 'Unknown error' }));
            throw new Error(`API error: ${response.status} - ${errorBody.error || errorBody.message || 'Server responded with an error.'}`);
        }

        const data = await response.json();
        console.log('API response:', data);

        // The backend returns an object with a 'recipes' key, which is an array of Recipe objects.
        // We need to extract that array.
        // Ensure data.recipes is indeed an array, otherwise return an empty array.
        return Array.isArray(data.recipes) ? data.recipes : [];

    } catch (error) {
        console.error('Failed to fetch recipes:', error);
        return []; // Return an empty array on error to prevent issues
    }
}

export default function Recipe() {
    // Initialize recipes state as null to indicate a loading state initially
    const [recipes, setRecipes] = useState<Recipe[] | null>(null);
    const [allergens] = useState<string[]>(() => {
        // Load allergens from localStorage only once when the component mounts
        const saved = localStorage.getItem('allergens');
        return saved ? JSON.parse(saved) : [];
    });

    useEffect(() => {
        // Fetch recipes when the component mounts or allergens change
        // We should explicitly handle the 'loading' state if desired
        setRecipes(null); // Set to null to show loading
        fetchRecipesFromAPI(allergens).then(data => {
            setRecipes(data); // Update with fetched recipes
        });
    }, [allergens]); // Re-run effect if allergens change

    return (
        <div className={styles.container}>
            <h1 className={styles.pageName}>Recipes</h1>

            <div className={styles.allergensSection}>
                <h2>Your Allergens:</h2>
                {allergens.length > 0 ? (
                    <ul className={styles.allergensList}>
                        {allergens.map((allergen, index) => (
                            <li key={index}>{allergen}</li>
                        ))}
                    </ul>
                ) : (
                    <p>No allergens selected. Go to Settings to add them.</p>
                )}
            </div>

            <h2 className={styles.recipesTitle} className={styles.recipesTitle}>Recipes:</h2>
            {recipes === null ? (
                <p className={styles.loadingText}>Loading recipes...</p>
            ) : recipes.length > 0 ? (
                <div className={styles.recipesGrid}>
                    {recipes.map((recipe, index) => (
                        <RecipeCard key={index} recipe={recipe} />
                    ))}
                </div>
            ) : (
                <p className={styles.noRecipes}>No recipes found with your current pantry items and allergies.</p>
            )}
        </div>
    );
}