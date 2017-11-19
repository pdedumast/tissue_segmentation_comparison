import numpy as np

from sklearn.model_selection import LeaveOneOut

from architectures.arch_creator import generate_model
from utils.callbacks import generate_callbacks, generate_output_filename
from utils.ioutils import read_dataset, save_volume
from utils.reconstruction import reconstruct_volume
from utils.training_testing_utils import split_train_val, build_training_set, build_testing_set

def run_evaluation_in_dataset(gen_conf, train_conf) :
    if train_conf['dataset'] == 'iSeg2017' :
        return evaluate_using_loo(gen_conf, train_conf)
    if train_conf['dataset'] == 'IBSR18' :
        return evaluate_using_loo(gen_conf, train_conf)
    if train_conf['dataset'] == 'MICCAI2012' :
        pass

def evaluate_using_loo(gen_conf, train_conf) :
    dataset_info = gen_conf['dataset_info'][train_conf['dataset']]
    num_modalities = dataset_info['modalities']
    num_volumes = dataset_info['num_volumes']
    input_data, labels = read_dataset(gen_conf, train_conf)

    loo = LeaveOneOut()
    for train_index, test_index in loo.split(range(num_volumes)):
        print train_index, test_index

        model, mean, std = train_model(
            gen_conf, train_conf, input_data[train_index], labels[train_index], test_index[0] + 1)

        test_vol = normalise_set(input_data[test_index], num_modalities, mean, std)[0]

        x_test = build_testing_set(gen_conf, train_conf, input_data[test_index[0]])
        test_model(gen_conf, train_conf, x_test, model, test_index[0]+1)

        del x_test

    return True

def train_model(
    gen_conf, train_conf, input_data, labels, case_name) :
    dataset_info = gen_conf['dataset_info'][train_conf['dataset']]
    num_modalities = dataset_info['modalities']
    
    train_index, val_index = split_train_val(
        range(len(input_data)), train_conf['validation_split'])

    mean, std = compute_statistics(input_data, num_modalities)
    input_data = normalise_set(input_data, num_modalities, mean, std)

    x_train, y_train = build_training_set(
        gen_conf, train_conf, input_data[train_index], labels[train_index])
    x_val, y_val = build_training_set(
        gen_conf, train_conf, input_data[val_index], labels[val_index])

    callbacks = generate_callbacks(
        gen_conf, train_conf, case_name)

    model = __train_model(
        gen_conf, train_conf, x_train, y_train, x_val, y_val, case_name, callbacks)

    return model, mean, std

def __train_model(gen_conf, train_conf, x_train, y_train, x_val, y_val, case_name, callbacks) :
    model = generate_model(gen_conf, train_conf)

    if train_conf['num_epochs'] != 0 :
        model.fit(
            x_train, y_train,
            epochs=train_conf['num_epochs'],
            validation_data=(x_val, y_val),
            verbose=train_conf['verbose'],
            callbacks=callbacks)

    model_filename = generate_output_filename(
        gen_conf['model_path'], train_conf['dataset'], case_name, train_conf['approach'], 'h5')

    model.load_weights(model_filename)

    return model

def test_model(gen_conf, train_conf, x_test, model, case_idx) :
    num_classes = gen_conf['num_classes']
    output_shape = train_conf['output_shape']

    pred = model.predict(x_test, verbose=1)
    pred = pred.reshape((len(pred), ) + output_shape + (num_classes, ))

    rec_vol = reconstruct_volume(gen_conf, train_conf, pred)

    save_volume(gen_conf, train_conf, rec_vol, case_idx)

def compute_statistics(input_data, num_modalities) :
    mean = np.zeros((num_modalities, ))
    std = np.zeros((num_modalities, ))

    for modality in range(num_modalities) :
        modality_data = input_data[:, modality]
        mean[modality] = np.mean(modality_data[modality_data != 0])
        std[modality] = np.std(modality_data[modality_data != 0])

    return mean, std

def normalise_set(input_data, num_modalities, mean, std) :
    input_data_tmp = np.copy(input_data)
    for vol_idx in range(len(input_data_tmp)) :
        for modality in range(num_modalities) :
            input_data_tmp[vol_idx, :, modality] -= mean[modality]
            input_data_tmp[vol_idx, :, modality] /= std[modality]
    return input_data_tmp