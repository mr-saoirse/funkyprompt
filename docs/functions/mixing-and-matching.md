---
description: How the agents mixes data and switches between strategies
---

# Mixing and matching

We want to explore how the agent switches between strategies.&#x20;

### A simple case: mixing domains in a single interpreter loop

As a warm up lets consider a simple case of breaking up a question and having to consult two stores. We have some books on habits and business and we also have fairy tales. These are domains that are not typically mixed

{% code overflow="wrap" %}
```
What are good tips for forming habits ? Can you consider some fairy tale characters in our data and suggest how one of them might change a particular habit? Reference the habit tips you outlined
```
{% endcode %}

Response

{% code overflow="wrap" fullWidth="false" %}
```
Good tips for forming habits:
1. Use implementation intentions: "I will [BEHAVIOR] at [TIME] in [LOCATION]."
2. Use habit stacking: "After [CURRENT HABIT], I will [NEW HABIT]."
3. Design your environment: Make the cues of good habits obvious and visible.
4. Use temptation bundling: Pair an action you want to do with an action you need to do.
5. Join a culture where your desired behavior is the normal behavior.
6. Create a motivation ritual: Do something you enjoy immediately before a difficult habit.
7. Reduce friction: Decrease the number of steps between you and your good habits.
8. Prime the environment: Prepare your environment to make future actions easier.
9. Master the decisive moment: Optimize the small choices that deliver outsized impact.
10. Use the Two-Minute Rule: Downscale your habits until they can be done in two minutes or less.
11. Automate your habits: Invest in technology and one-time purchases that lock in future behavior.

For a fairy tale character, let's consider Cinderella from "The Story of Cinderella." Cinderella could change her habit of procrastination and staying out too late (which caused her to run from the ball and leave her slipper behind when the clock struck twelve) by implementing the following changes:

1. Use implementation intentions: Cinderella could plan her departure ahead of time by saying, "I will leave the ball at [TIME] to ensure I return home before my gown turns to rags."
2. Use habit stacking: "After the last dance, I will say my goodbyes and leave the ball."
3. Design her environment: Cinderella could set a reminder or carry a small clock to keep track of the time while at the ball.
4. Create a motivation ritual: Cinderella could plan a relaxing activity or a reward for herself when she gets home early, reinforcing her desire to leave on time.

By applying these habit formation strategies, Cinderella could avoid the negative consequences of her procrastination, such as losing her glass slipper and running the risk of not making it home on time.

I provided these suggestions based on established habit-forming tips and the character's storyline as found in the fairy tales vector search results, which should offer a practical and imaginative approach to habit change for Cinderella.
```
{% endcode %}

The response requires the interpreter loop to keep running until it has answered the question. It will load functions to answer sub parts and then combined the answer. This is the simplest case.

### 2 Traverse hints and links from data



