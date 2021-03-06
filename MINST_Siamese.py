''' Based on https://github.com/keras-team/keras/blob/master/examples/mnist_siamese.py
    Just to try it out.
'''
import random

import numpy as np

import keras.backend as K
from keras.models import Model
from keras.layers import Input, Dense, Conv2D, Dropout, MaxPool2D, Flatten, Lambda
from keras.datasets import mnist
from keras.optimizers import Adam

epochs = 20
num_classes = 10

def euclidean_distance(vects):
    x, y = vects
    return K.sqrt(K.maximum(K.sum(K.square(x - y), axis=1, keepdims=True), K.epsilon()))


def eucl_dist_output_shape(shapes):
    shape1, _ = shapes
    return (shape1[0], 1)


def contrastive_loss(y_true, y_pred):
    '''Contrastive loss from Hadsell-et-al.'06
    http://yann.lecun.com/exdb/publis/pdf/hadsell-chopra-lecun-06.pdf
    '''
    margin = 1
    return K.mean(y_true * K.square(y_pred) +
                  (1 - y_true) * K.square(K.maximum(margin - y_pred, 0)))


def create_pairs(x, digit_indices):
    '''Positive and negative pair creation.
    Alternates between positive and negative pairs.
    '''
    pairs = []
    labels = []
    n = min([len(digit_indices[d]) for d in range(num_classes)]) - 1
    for d in range(num_classes):
        for i in range(n):
            z1, z2 = digit_indices[d][i], digit_indices[d][i + 1]
            pairs += [[x[z1], x[z2]]]
            inc = random.randrange(1, num_classes)
            dn = (d + inc) % num_classes
            z1, z2 = digit_indices[d][i], digit_indices[dn][i]
            pairs += [[x[z1], x[z2]]]
            labels += [1, 0]
    return np.array(pairs), np.array(labels)

def create_base_model():
    input = Input(shape=(28,28,1))
    x = Conv2D(filters=8, kernel_size=5, padding='same')(input)
    x = Dropout(0.1)(x)
    x = Conv2D(filters=8, kernel_size=5, padding='same')(x)
    x = Dropout(0.1)(x)
    x = MaxPool2D()(x)
    x = Flatten()(x)
    x = Dense(64, activation='relu')(x)
    x = Dropout(0.1)(x)
    x = Dense(64, activation='relu')(x)
    return Model(input, x)

def compute_accuracy(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    pred = y_pred.ravel() < 0.5
    return np.mean(pred == y_true)


def accuracy(y_true, y_pred):
    '''Compute classification accuracy with a fixed threshold on distances.
    '''
    return K.mean(K.equal(y_true, K.cast(y_pred < 0.5, y_true.dtype)))


# Fetch data and rescale.
(x_train, y_train), (x_test, y_test) = mnist.load_data()
x_train = np.reshape(x_train, x_train.shape + (1,))
x_train = x_train.astype('float32')
x_test = x_test.astype('float32')
x_test = np.reshape(x_test, x_test.shape + (1,))
x_train /= 255
x_test /= 255
input_shape = x_train.shape[1:]

# Create positive and negative pairs.
digit_indices = [np.where(y_train == i)[0] for i in range(num_classes)]
tr_pairs, tr_y = create_pairs(x_train, digit_indices)

digit_indices = [np.where(y_test == i)[0] for i in range(num_classes)]
te_pairs, te_y = create_pairs(x_test, digit_indices)

# Get the siamese network.
base_net = create_base_model()

inputA = Input(shape=(28,28,1))
inputB = Input(shape=(28,28,1))

branchA = base_net(inputA)
branchB = base_net(inputB)

distance = Lambda(euclidean_distance, output_shape=eucl_dist_output_shape)([branchA, branchB])

model = Model([inputA, inputB], distance)

# train
opt = Adam()
model.compile(loss=contrastive_loss, optimizer=opt, metrics=[accuracy])
model.fit([tr_pairs[:, 0], tr_pairs[:, 1]], tr_y,
          batch_size=128,
          epochs=epochs,
          validation_data=([te_pairs[:, 0], te_pairs[:, 1]], te_y))

# Compute final accuracy on training and test set.
y_pred = model.predict([tr_pairs[:, 0], tr_pairs[:, 1]])
tr_acc = compute_accuracy(tr_y, y_pred)
y_pred = model.predict([te_pairs[:, 0], te_pairs[:, 1]])
te_acc = compute_accuracy(te_y, y_pred)

print('* Accuracy on training set: %0.2f%%' % (100 * tr_acc))
print('* Accuracy on test set: %0.2f%%' % (100 * te_acc))