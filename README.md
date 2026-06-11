# OmniLab

<img width="400" height="250" alt="OmniLab" src="https://github.com/user-attachments/assets/0009a603-df50-4d0f-b299-ce9f8b2e79a8" />

## Inspiration
The inspiration came from remembering how static and unengaging school chemistry textbooks could be, combined with the lack of accessible, high-quality laboratory equipment in many remote schools. I wanted to build a bridge between complex chemical theory and interactive visual learning. By leveraging advanced AI alongside modern web rendering techniques, I realized I could create a safe, virtual environment where anyone could experiment with chemicals without real-world hazards.

## What it does
OmniLab AI is an interactive, academic-grade chemistry simulator that visualizes and find chemical reactions in real time. Users can select and mix compounds within three dynamic glass vessels (Flasks, Beakers, or Test Tubes), apply thermal heat using a virtual Bunsen burner, and see advanced physics-based fluid animations. Instantly, the backend processes the mixture to output balanced molecular equations, thermodynamics analysis, high-density explanations, and critical safety rules with active command verbs for physical execution.

<p display="flex" flex-direction="row" justify-content="center">
  <video src="https://github.com/user-attachments/assets/53149a98-4826-48ca-8b86-f2b7dfec6e22" width="49%" controls></video>
  <video src="https://github.com/user-attachments/assets/51316f66-a813-44b8-8e55-8c38fafe35c9" width="49%" controls></video>
</p>

## How I built it
I engineered OmniLab AI using a powerful, multi-layered architecture. The backend is powered by Django, utilizing custom prompt structures connected to LLM APIs for robust JSON processing of reaction analytics. On the frontend, I crafted a high-performance rendering system using HTML5 Canvas and Vanilla JavaScript (ESModules) to simulate real-time fluid waves, dynamic color transitions, and particle-based boiling effects. I also used Bootstrap 5 for a responsive layout and configured a secure .env system for infrastructure stability.

## Challenges I ran into
One of the toughest challenges was managing the asynchronous state cycle between the AI payload and the frontend rendering loops. Initially, the Canvas loop would try to update fluid colors before the JSON response fully resolved, leading to null pointer exceptions (TypeError: Cannot read properties of null (reading 'map')). I also faced edge cases where complex mixtures caused JSON formatting mismatches, which required designing strict validation structures and solid fallback error-handling loops on the client side.

## Accomplishments that I'm proud of
I am incredibly proud of creating a seamless fluid animation system that mathematically calculates fluid height and wave behavior relative to the chosen glassware. Achieving a smooth, cross-fading color transition algorithm that morphs the liquid based on the reaction outcome was a big win. Additionally, creating a highly functional and responsive user interface that switches beautifully between light and dark modes while keeping layout consistency felt deeply rewarding.

## What's next for OmniLab AI
The next phase of OmniLab AI will focus on scaling both the laboratory inventory and the rendering complexity. First, I plan to introduce a much wider variety of laboratory apparatus—such as volumetric pipettes, condenser tubes, and distillation setups—while engineering a system that allows them to interconnectedly work together as a synchronized pipeline. Furthermore, I will push the boundaries of the visual engine by optimizing fluid physics, adding intricate phase-change indicators, and implementing advanced thermodynamic visual effects to make the digital experimentation feel even more realistic and immersive.
