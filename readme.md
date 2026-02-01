### IC-Hack 2026

## Inspiration

Humans are great at remembering things. _We_ remembered to wake up at 7 for this presentation, and _you’ll_ probably remember us after you leave. But we’re not perfect. We forget to take out the trash. We forget how to solve second-order differential equations from high school. And, more often than we’d like to admit, we forget what we have in our fridge... and our pantry, cupboards, and shelves.

When that happens, food gets forgotten. It goes bad. And when we don’t know what we have, we don't know what we can make. Or god forbid you're in a student accommodation and your can of beans gets stolen. You're not finding that out till next week. 

But there's a surprisingly simple way to not forget. And that's to always be looking.

## What it does

**ShelfLife** is a low-cost smart pantry system that keeps track of food items in real time.

- Maintains an up-to-date digital inventory of pantry items that users can view and edit through a mobile app  
- Automatically detects when items are added or removed  
- Suggests recipes based on available ingredients, prioritising items closest to expiry  
- Flags foods at risk of expiring and notifies users to reduce waste  
- Supports multiple cupboards that can link together into a single system  

The goal is to reduce food waste while making meal planning easier and more intuitive.

## How we built it

ShelfLife is built as a full-stack system combining hardware, AI, and a mobile-first interface.

- **Frontend:** React-based web app, packaged using **Tauri** to run smoothly on Android devices  
- **Backend:** LangChain orchestrating **Gemini** for vision-language reasoning and inventory updates  
- **Hardware:**  
- **ESP32-CAM** to capture images of the pantry  
- **Ultrasonic sensor** to detect when the pantry is opened or when items are placed or removed  

When a change is detected, the system captures **before and after images** of the pantry and sends them to the server for processing. The backend compares the images, identifies changes, and updates the inventory accordingly.

## Challenges we ran into

One major challenge was using traditional image processing models. Due to limited training data, accuracy was poor. We pivoted to **vision-language models (VLMs)**, which performed significantly better with fewer assumptions.

Another challenge was determining whether an item had been added or removed. We solved this by capturing before-and-after images and comparing them rather than relying on a single snapshot.

Lighting was also an issue in enclosed cupboards, so we used the **ESP32-CAM’s onboard LED** to illuminate the pantry at the moment an image is taken, greatly improving image quality.

## Accomplishments that we're proud of

- Successfully deploying a React web app onto Android devices using Tauri  
- Integrating real-time hardware input with AI-powered backend reasoning  
- Building a working end-to-end prototype that combines sensing, vision, and user interaction  
- Designing a system that is modular, affordable, and scalable beyond a single cupboard  

## What we learned

- Vision-language models are far more flexible than traditional image processing when data is limited  
- Hardware constraints (lighting, angles, sensor timing) have a huge impact on AI reliability  
- Building for mobile early prevents major integration issues later  
- Simple design decisions (like before-and-after comparisons) can dramatically improve robustness  

## What's next for ShelfLife

- Adding **calorie estimation** to help users track nutritional intake  
- Improving camera placement and sensing accuracy  
- Integrating **RFID tags** to enable precise tracking of individual items and more accurate expiry dates  
- Expanding the system for shared environments like dorms, offices, and educational spaces  
