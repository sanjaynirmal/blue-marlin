# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
#                                                 * "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.

import numpy as np

class DataInput:
  def __init__(self, data, batch_size):

    self.batch_size = batch_size
    self.data = data
    self.epoch_size = len(self.data) // self.batch_size
    if self.epoch_size * self.batch_size < len(self.data):
      self.epoch_size += 1
    self.i = 0

  def __iter__(self):
    return self

  def next(self):
    return self.__next__()

  def __next__(self):

    if self.i == self.epoch_size:
      raise StopIteration

    ts = self.data[self.i * self.batch_size : min((self.i+1) * self.batch_size,
                                                  len(self.data))]
    self.i += 1

    u, i, y, sl = [], [], [], []
    for t in ts:
      u.append(t[0])
      i.append(t[2])
      y.append(t[3])
      sl.append(len(t[1]))
    max_sl = max(sl)

    hist_i = np.zeros([len(ts), max_sl], np.int64)

    k = 0
    for t in ts:
      for l in range(len(t[1])):
        hist_i[k][l] = t[1][l]
      k += 1

    return self.i, (u, i, y, hist_i, sl)

class DataInputTest:
  def __init__(self, data, batch_size):

    self.batch_size = batch_size
    self.data = data
    self.epoch_size = len(self.data) // self.batch_size
    if self.epoch_size * self.batch_size < len(self.data):
      self.epoch_size += 1
    self.i = 0

  def __iter__(self):
    return self

  def next(self):
    return self.__next__()

  def __next__(self):

    if self.i == self.epoch_size:
      raise StopIteration

    ts = self.data[self.i * self.batch_size : min((self.i+1) * self.batch_size,
                                                  len(self.data))]
    self.i += 1

    u, i, j, sl = [], [], [], []
    for t in ts:
      u.append(t[0])
      i.append(t[2][0])
      j.append(t[2][1])
      sl.append(len(t[1]))
    max_sl = max(sl)

    hist_i = np.zeros([len(ts), max_sl], np.int64)

    k = 0
    for t in ts:
      for l in range(len(t[1])):
        hist_i[k][l] = t[1][l]
      k += 1

    return self.i, (u, i, j, hist_i, sl)
