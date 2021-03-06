#!/usr/bin/env python
from __future__ import print_function
import numpy as np
from random import randint, random, choice, seed

from multitilecoding import multitilecoder
import mountaincar

class QSigma:
  def __init__(self, steps=1, init_sigma=1.0, epsilon=0.1, step_size=0.1, beta=1.0):
    # Qsigma parameters
    self._n = steps
    self._sig = init_sigma
    self._beta = beta
    # num actions
    self._n_actions = 3
    # tilecoder
    tilings = 8
    dims = [8, 8]
    lims = [(-1.2, 0.5), (-0.07, 0.07)]
    offset_vec = [1, 3]
    self._Q = multitilecoder(self._n_actions, dims, lims, tilings, step_size, offset_vec)
    # eps greedy
    self._eps = epsilon

  def episode(self, discount=1.0, max_steps=1e3):
    """ Run n-step Q(sigma) for one episode """
    self._s = mountaincar.init()
    self._r_sum = 0.0
    self._time = 0 # step counter
    self._T = float('inf')
    self._tau = 0
    action = self.pick_action(self._s)
    self._tr = [(self._s, self._r_sum)] * self._n
    self._delta = [0.0] * self._n
    self._Qt = [self._Q[self._s, action]] * (self._n + 1)
    self._pi = [0.0] * self._n
    self._sigma = [0.0] * self._n
    while (self._tau != (self._T - 1)) and (self._time < max_steps):
      action = self.act(action, discount)
    self._sig *= self._beta
    return self._r_sum

  def act(self, action, discount):
    """ do an action and update Q given the discount factor and step size """
    if self._time < self._T:
        (r, sp) = mountaincar.sample(self._s, action)
        self._r_sum += r
        self._tr[self._time % self._n] = (self._s, action)
        if sp == None: # if terminal
            self._T = self._time + 1
            self._delta[self._time%self._n] = r - self._Qt[self._time%(self._n+1)] # TD error
        else: # commit the next action
            action = self.pick_action(sp) # select arbitrarily and store an action as A_(t+1)
            self._Qt[(self._time + 1)%(self._n+1)] = self._Q[sp, action] # Store Q(St+1;At+1) as Qt+1
            self._sigma[(self._time+1)%self._n] = self._sig
            self._delta[self._time%self._n] = r - self._Qt[self._time%(self._n+1)] + \
              discount*((1-self._sigma[(self._time+1)%self._n]) * self.expected_Q(sp) + self._sigma[(self._time+1)%self._n] * self._Q[sp, action])
            self._pi[(self._time+1)%self._n] = self.get_action_probability(sp, action)
        self._s = sp # update agent state
    self._tau = self._time + 1 - self._n # time whose estimate is being updated
    if self._tau >= 0:
        E = 1.0
        G = self._Qt[self._tau%(self._n+1)]
        for k in range(self._tau, int(min(self._time, self._T-1))+1):
            G += E * self._delta[k%self._n]
            E *= discount * ((1-self._sigma[(k+1)%self._n]) * self._pi[(k+1)%self._n] + self._sigma[(k+1)%self._n])
        s, a = self._tr[self._tau%self._n]
        self._Q[s, a] = G
    self._time += 1
    return action # return the committed next action

  def get_action_probability(self, state, action):
    """ return the action probability at a state of a given policy P[s][a] """
    Qs = [0.0] * self._n_actions
    for a in range(self._n_actions):
      Qs[a] = self._Q[state, a]
    if Qs[action] == max(Qs):
        return self._eps/self._n_actions + (1.0 - self._eps)/Qs.count(max(Qs))
    else:
        return self._eps/self._n_actions

  def pick_action(self, state):
    """ return an action according to a given policy P[s][a] """
    if random() < self._eps:
      return randint(0, self._n_actions - 1)
    else:
      Qs = [0.0] * self._n_actions
      for a in range(self._n_actions):
        Qs[a] = self._Q[state, a]
      max_Q = max(Qs)
      indices = [i for i, x in enumerate(Qs) if x == max_Q]
      if len(indices) == 1:
          return indices[0]
      else: # break ties randomly to prevent the case where committing to one action leads to no reward
          return choice(indices)

  def expected_Q(self, state):
    """ get the expected Q under a target policy """
    Qs = [0.0] * self._n_actions
    for a in range(self._n_actions):
      Qs[a] = self._Q[state, a]
    Q_exp = (1.0 - self._eps) * max(Qs)
    for a in range(self._n_actions):
      Q_exp += (self._eps / self._n_actions) * Qs[a]
    return Q_exp

def example():
  import matplotlib.pyplot as plt
  from mpl_toolkits.mplot3d import Axes3D

  n_runs = 10
  n_eps = 100
  ep_avg_R = 0.0
  avg_R = 0.0

  for run in range(1, n_runs + 1):
    agent = QSigma(3, 0.5, 0.1, 0.7, 1.0)
    for episode in range(1, n_eps + 1):
      R = agent.episode(1.0, 10000)
      ep_avg_R += (1 / episode) * (R - ep_avg_R)
      print('episode:', episode, 'sigma:', round(agent._sig / 0.95, 2), 'reward:', R)
    print('run:', run, 'mean reward:', ep_avg_R)
    avg_R += (1 / run) * (ep_avg_R - avg_R)
  print('overall avg reward:', avg_R)

  print('mapping function...')
  res = 200
  x = np.arange(-1.2, 0.5, (0.5 + 1.2) / res)
  y = np.arange(-0.07, 0.07, (0.07 + 0.07) / res)
  z = np.zeros([len(y), len(x)])
  for i in range(len(x)):
    for j in range(len(y)):
      s = (x[i], y[j])
      Q_max = agent._Q[s, 0]
      for a in range(1, agent._n_actions):
        if agent._Q[s, a] > Q_max:
          Q_max = agent._Q[s, a]
      z[j, i] = -Q_max

  # plot
  fig = plt.figure()
  ax = fig.gca(projection='3d')
  X, Y = np.meshgrid(x, y)
  surf = ax.plot_surface(X, Y, z, cmap=plt.get_cmap('hot'))
  plt.show()

if __name__ == '__main__':
  example()