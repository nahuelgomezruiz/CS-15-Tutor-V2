import os
from llmproxy import generate, retrieve

"""
Categorize a student query using LLM
"""
categorization_prompt = f"""
        Categorize this CS 15 student query into exactly one of these categories:
        
        - Homework Help: Questions about implementing assignments, debugging code, or getting help with specific project requirements (CS15 projects are called: Array Lists, Linked Lists, CalcYouLater, MetroSim, Zap, Typewriter, and Gerp)
        - Explanation of Concepts: Questions about understanding data structures, algorithms, C++ concepts, or theoretical topics
        - Course Information: Questions about course logistics, policies, deadlines, or administrative matters
        - Unrelated to Course: Questions that are not related to CS 15 content, programming, or course administration
        
        Student Query: "can you help me with metro sim please"
        
        Return ONLY the category name, nothing else.
        """

try:
    response = generate(
        model='4o-mini',
        system="be nice",
        query=categorization_prompt,
        temperature=0.1,  # Low temperature for consistent categorization
        lastk = 0,
        rag_usage=False,
    )

    category_text = response
    
except Exception as e:
    print(f"❌ Error categorizing query: {e}")
    category_text = "Error"

print(f"🔍 Categorization result: {category_text}")
