---
description: When and how to generically prompt for reasoning
---

# 6 Logic Problems

{% code overflow="wrap" %}
````
# this is a prompt with embedded text:>

Consider the text below. How similar do the two occasions sound? 
In how many situations do you think Snow White received warnings and what were the total number of warnings she received?
Is it possible they are referring to the same situation? What probability would you assign that they are the same.
If the situations sound sufficiently similar i.e. if the probability they are similar is greater than 0.7, you can assume they are in fact the same events.
If they are the same events, you can assume that the mentioned warnings are the same warnings and should be counted once in total.
BAsed on your probability of them being the same event, what were the total number of unique events, and the total number of warnings
TEXT:
```
Snow White receives warnings. \n\n1) In a story summary, it was mentioned that after finding Snow-White lying unconscious, the dwarfs suspect the wicked Queen. They revive her by removing a poisoned comb and warn her to beware of her stepmother. \n\n2) In another scene, the dwarfs return to find Snow-White lying like dead on the ground. Immediately identifying the poisoned comb from the Queen, they extract it, reviving the young maiden. They then reiterate their warning about the wicked stepmother and advise her not to open the door to anyone.\n\nThese occasions display Snow White's dangerous encounters and the protective guidance provided by the dwarfs against her wicked stepmother
```
````
{% endcode %}

I show the final result which was actually a struggle for the agent. Both to know that the situations are distinct and that the number of warnings are distinctly 1

{% code overflow="wrap" %}
```
Based on the text, the two occasions provided appear very similar, almost identical - in both instances, Snow White is found unconscious, the dwarfs revive her by removing a poisoned comb, and they warn her about her wicked stepmother. Therefore, it can be assumed with high probability they are the same event. \n\nThus, according to the rules set in the question, since the probability they are similar is greater than 0.7, we can assume they are in fact the same. Consequently, the warnings should be counted once in total.\n\nTherefore, there was 1 unique event, and Snow White received 1 warning based on the text provided.
```
{% endcode %}

The problem is we cannot handhold the agent. How would we make this a module that can be used - how does the agent even know it needs to invoke such reasoning? We could probably but this in a general - rules for counting module since counting is the general combinatorics brain teaser.&#x20;

{% hint style="info" %}
I discovered this when adding story summaries. What is interesting about summaries is you can pull back two instances of an event in a search so the agent may in fact assume that something else happened "later". Another way for the agent to dig itself out above would be not to double counting data and summaries of data. In our stores, this is like not mixing data from multiple text "depths"&#x20;
{% endhint %}

Another prompt we can try is grouping

{% code overflow="wrap" fullWidth="false" %}
```
Consider the text below. In each event, look for evidence that it is the same as another event.
Group all events into the smallest possible number of groups. What are these groups? Give a simple name for each group.
Considering your final groups, what do you think was the total number of unique groups were snow white was warnned?

```
{% endcode %}

results in...

{% code overflow="wrap" %}
```
Based on the text provided, all the events can be grouped into one group which can be simply named as "Warnings to Snow White". \n\nIn both events, the dwarfs revive Snow White and warn her against her wicked stepmother. Therefore, there was only one unique group where Snow White was warned.
```
{% endcode %}
