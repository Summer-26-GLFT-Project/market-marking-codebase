#!/usr/bin/env python
# coding: utf-8

# In[17]:


import numpy as np
import matplotlib.pyplot as plt

# Model parameters
VH = 110
VL = 90
mu = 0.3        
pi = 0.5 
n_trades = 200
true_value = VH
np.random.seed(42)

beliefs = [pi]
orders = []
asks = []
bids = []

def bayesian_update(pi, order, mu):
    if order == "buy":
        p_buy_VH = mu + 0.5 * (1 - mu)   
        p_buy_VL = 0.5 * (1 - mu)         
        denom = pi * p_buy_VH + (1 - pi) * p_buy_VL
        return pi * p_buy_VH / denom
    else:
        p_sell_VH = 0.5 * (1 - mu)        
        p_sell_VL = mu + 0.5 * (1 - mu)  
        denom = pi * p_sell_VH + (1 - pi) * p_sell_VL
        return pi * p_sell_VH / denom

for t in range(n_trades):
    pi_if_buy  = bayesian_update(pi, "buy",  mu)
    pi_if_sell = bayesian_update(pi, "sell", mu)

    ask = VH * pi_if_buy  + VL * (1 - pi_if_buy)   
    bid = VH * pi_if_sell + VL * (1 - pi_if_sell)
    asks.append(ask)
    bids.append(bid)

    is_informed = np.random.rand() < mu
    if is_informed:
        order = "buy" if true_value == VH else "sell"
    else:
        order = "buy" if np.random.rand() < 0.5 else "sell"
    orders.append(order)

    pi = bayesian_update(pi, order, mu)
    beliefs.append(pi)

# Plot 
plt.figure(figsize=(10, 5))
plt.plot(beliefs, label="Posterior P(V = VH)")
plt.axhline(1, linestyle="--", color="gray", label="True state: High")
plt.xlabel("Trade Number")
plt.ylabel("Belief P(V = VH)")
plt.title("Glosten-Milgrom: Public Belief Convergence")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

plt.figure(figsize=(10, 5))
plt.plot(asks, label="Ask Quote")
plt.plot(bids, label="Bid Quote")
plt.xlabel("Trade Number")
plt.ylabel("Quote ($)")
plt.title("Bid and Ask Quotes over Time")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

print(f"Final belief P(V = VH): {beliefs[-1]:.4f}")
print(f"Buy orders: {orders.count('buy')}, Sell orders: {orders.count('sell')}")
print(f"Final ask: {asks[-1]:.4f}, Final bid: {bids[-1]:.4f}")


# In[ ]:


# Interpretation:

# Bid and ask quotes are conditional expectations of the asset value given an observed sell or buy order.
# As the market maker becomes more certain that the true value is VH, both quotes converge toward VH.
# The bid-ask spread narrows over time because information uncertainty decreases.
# Once the market fully learns the true state, bid and ask become nearly identical.


# In[ ]:


# Make comparion with different mu_values


# In[16]:


import numpy as np
import matplotlib.pyplot as plt

VH = 110
VL = 90
pi0 = 0.5
n_trades = 1000
true_value = VH
mu_values = [0.05, 0.15, 0.30]
np.random.seed(42)

def bayesian_update(pi, order, mu):
    if order == "buy":
        p_VH = mu + 0.5 * (1 - mu)
        p_VL = 0.5 * (1 - mu)
    else:
        p_VH = 0.5 * (1 - mu)
        p_VL = mu + 0.5 * (1 - mu)
    denom = pi * p_VH + (1 - pi) * p_VL
    return pi * p_VH / denom

plt.figure(figsize=(10, 5))

for mu in mu_values:
    pi = pi0
    beliefs = [pi]
    for t in range(n_trades):
        is_informed = np.random.rand() < mu
        order = ("buy" if true_value == VH else "sell") if is_informed \
                else ("buy" if np.random.rand() < 0.5 else "sell")
        pi = bayesian_update(pi, order, mu)
        beliefs.append(pi)
    plt.plot(beliefs, label=f"$\\mu$ = {mu}")

plt.axhline(1, linestyle="--", color="gray", label="True state: High")
plt.xlabel("Trade Number")
plt.ylabel("Belief $P(V = V_H)$")
plt.title("Belief Convergence for Different Informed Trader Probabilities")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()


# In[ ]:


# Interpretation:

# The parameter mu represents the probability that an arriving trader is informed.
# Higher values of mu make order flow more informative.
# When mu = 0.30, beliefs converge rapidly because many traders possess information about the true value.
# This result confirms the Glosten-Milgrom prediction that markets with a larger informed-trader presence learn the true asset value more quickly.

