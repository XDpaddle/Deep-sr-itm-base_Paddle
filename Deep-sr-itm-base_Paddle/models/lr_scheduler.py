import math
from collections import Counter
from collections import defaultdict
import paddle
from paddle.optimizer.lr import LRScheduler

class MultiStepLR_Restart(LRScheduler):
    def __init__(self, optimizer, milestones, restarts=None, weights=None, gamma=0.1,
                 clear_state=False, last_epoch=-1):
        self.milestones = Counter(milestones)
        self.gamma = gamma
        self.clear_state = clear_state
        self.restarts = restarts if restarts else [0]
        self.restarts = [v + 1 for v in self.restarts]
        self.restart_weights = weights if weights else [1]
        assert len(self.restarts) == len(
            self.restart_weights), 'restarts and their weights do not match.'
        super(MultiStepLR_Restart, self).__init__(optimizer, last_epoch)

    def get_lr(self):
        if self.last_epoch in self.restarts:
            if self.clear_state:
                self.optimizer.state = defaultdict(dict)
            weight = self.restart_weights[self.restarts.index(self.last_epoch)]
            return [group['initial_lr'] * weight for group in self.optimizer.param_groups]
        if self.last_epoch not in self.milestones:
            return [group['lr'] for group in self.optimizer.param_groups]
        return [
            group['lr'] * self.gamma**self.milestones[self.last_epoch]
            for group in self.optimizer.param_groups
        ]


class CosineAnnealingLR_Restart(LRScheduler):
    def __init__(self, optimizer, T_period, restarts=None, weights=None, eta_min=0, last_epoch=-1):
        self.T_period = T_period
        self.T_max = self.T_period[0]  # current T period
        self.eta_min = eta_min
        self.restarts = restarts if restarts else [0]
        self.restarts = [v + 1 for v in self.restarts]
        self.restart_weights = weights if weights else [1]
        self.last_restart = 0
        self.optimizer = optimizer
        self.optimizer._learning_rate = self
        assert len(self.restarts) == len(
            self.restart_weights), 'restarts and their weights do not match.'
        super(CosineAnnealingLR_Restart, self).__init__(optimizer.get_lr(), last_epoch)

    def get_lr(self):
        if self.last_epoch == 0:
            # return self.base_lrs
            return [self.base_lr]
        elif self.last_epoch in self.restarts:
            self.last_restart = self.last_epoch
            self.T_max = self.T_period[self.restarts.index(self.last_epoch) + 1]
            weight = self.restart_weights[self.restarts.index(self.last_epoch)]
            return [self.base_lr * weight ]
        elif (self.last_epoch - self.last_restart - 1 - self.T_max) % (2 * self.T_max) == 0:
            return [
                self.optimizer.get_lr() + (self.base_lr - self.eta_min) * (1 - math.cos(math.pi / self.T_max)) / 2
            ]
        return [(1 + math.cos(math.pi * (self.last_epoch - self.last_restart) / self.T_max)) /
                (1 + math.cos(math.pi * ((self.last_epoch - self.last_restart) - 1) / self.T_max)) *
                (self.optimizer.get_lr()[0] - self.eta_min) + self.eta_min
                ]
                # for group in self.optimizer.param_groups]


class CosineAnnealingDecay(LRScheduler):
    r"""
    Set the learning rate using a cosine annealing schedule, where :math:`\eta_{max}` is set to
    the initial learning_rate. :math:`T_{cur}` is the number of epochs since the last restart in
    SGDR.
    The algorithm can be described as following.
    .. math::
        \eta_t & = \eta_{min} + \frac{1}{2}(\eta_{max} - \eta_{min})\left(1
        + \cos\left(\frac{T_{cur}}{T_{max}}\pi\right)\right),
        & T_{cur} \neq (2k+1)T_{max};
        \eta_{t+1} & = \eta_{t} + \frac{1}{2}(\eta_{max} - \eta_{min})
        \left(1 - \cos\left(\frac{1}{T_{max}}\pi\right)\right),
        & T_{cur} = (2k+1)T_{max}.

    It has been proposed in `SGDR: Stochastic Gradient Descent with Warm Restarts <https://arxiv.org/abs/1608.03983>`_.
    Note that this only implements the cosine annealing part of SGDR, and not the restarts.

    Args:
        learning_rate (float): The initial learning rate, that is :math:`\eta_{max}` . It can be set to python float or int number.
        T_max (int): Maximum number of iterations. It is half of the decay cycle of learning rate. It must be a positive integer.
        eta_min (float|int, optional): Minimum learning rate, that is :math:`\eta_{min}` . Default: 0.
        last_epoch (int, optional):  The index of last epoch. Can be set to restart training. Default: -1, means initial learning rate.
        verbose (bool, optional): If ``True``, prints a message to stdout for each update. Default: ``False`` .
    Returns:
        ``CosineAnnealingDecay`` instance to schedule learning rate.
    Examples:

        .. code-block:: python
            import paddle
            import numpy as np
            # train on default dynamic graph mode
            linear = paddle.nn.Linear(10, 10)
            scheduler = paddle.optimizer.lr.CosineAnnealingDecay(learning_rate=0.5, T_max=10, verbose=True)
            sgd = paddle.optimizer.SGD(learning_rate=scheduler, parameters=linear.parameters())
            for epoch in range(20):
                for batch_id in range(5):
                    x = paddle.uniform([10, 10])
                    out = linear(x)
                    loss = paddle.mean(out)
                    loss.backward()
                    sgd.step()
                    sgd.clear_gradients()
                    scheduler.step()    # If you update learning rate each step
              # scheduler.step()        # If you update learning rate each epoch
            # train on static graph mode
            paddle.enable_static()
            main_prog = paddle.static.Program()
            start_prog = paddle.static.Program()
            with paddle.static.program_guard(main_prog, start_prog):
                x = paddle.static.data(name='x', shape=[None, 4, 5])
                y = paddle.static.data(name='y', shape=[None, 4, 5])
                z = paddle.static.nn.fc(x, 100)
                loss = paddle.mean(z)
                scheduler = paddle.optimizer.lr.CosineAnnealingDecay(learning_rate=0.5, T_max=10, verbose=True)
                sgd = paddle.optimizer.SGD(learning_rate=scheduler)
                sgd.minimize(loss)
            exe = paddle.static.Executor()
            exe.run(start_prog)
            for epoch in range(20):
                for batch_id in range(5):
                    out = exe.run(
                        main_prog,
                        feed={
                            'x': np.random.randn(3, 4, 5).astype('float32'),
                            'y': np.random.randn(3, 4, 5).astype('float32')
                        },
                        fetch_list=loss.name)
                    scheduler.step()    # If you update learning rate each step
              # scheduler.step()        # If you update learning rate each epoch
    """

    def __init__(self,
                 learning_rate,
                 T_period,
                 restarts=None,
                 weights=None,
                 eta_min=0,
                 last_epoch=-1,
                 verbose=False):
        self.T_period = T_period
        self.T_max = self.T_period[0]
        self.eta_min = float(eta_min)
        self.restarts = restarts if restarts else [0]
        self.restarts = [v + 1 for v in self.restarts]
        self.restart_weights = weights if weights else [1]
        self.last_restart = 0
        super(CosineAnnealingDecay, self).__init__(learning_rate, last_epoch,
                                                   verbose)
    def get_lr(self):
        if self.last_epoch == 0:
            return self.base_lr
        elif self.last_epoch in self.restarts:
            self.last_restart = self.last_epoch
            self.T_max = self.T_period[self.restarts.index(self.last_epoch) + 1]
            weight = self.restart_weights[self.restarts.index(self.last_epoch)]
            return self.base_lr * weight
        elif (self.last_epoch - self.last_restart - 1 - self.T_max) % (2 * self.T_max) == 0:
            return self.last_lr + (self.base_lr - self.eta_min) * (1 - math.cos(math.pi/self.T_max)) / 2
        return (1 + math.cos(math.pi * (self.last_epoch - self.last_restart) / self.T_max)) / (1 + math.cos(math.pi * ((self.last_epoch - self.last_restart) - 1) / self.T_max)) * (self.last_lr - self.eta_min) + self.eta_min

    def _get_closed_form_lr(self):
        return self.eta_min + (self.base_lr - self.eta_min) * (1 + math.cos(
            math.pi * self.last_epoch / self.T_max)) / 2


if __name__ == "__main__":
    linear = paddle.nn.Linear(10, 10)
    optimizer = paddle.optimizer.Adam(parameters=linear.parameters(), learning_rate=5e-7, weight_decay=5e-4,
                                 beta1=0.9, beta2=0.99)
    ##############################
    # MultiStepLR_Restart
    ##############################
    ## Original
    lr_steps = [200000, 400000, 600000, 800000]
    restarts = None
    restart_weights = None

    ## two
    lr_steps = [100000, 200000, 300000, 400000, 490000, 600000, 700000, 800000, 900000, 990000]
    restarts = [500000]
    restart_weights = [1]

    ## four
    lr_steps = [
        50000, 100000, 150000, 200000, 240000, 300000, 350000, 400000, 450000, 490000, 550000,
        600000, 650000, 700000, 740000, 800000, 850000, 900000, 950000, 990000
    ]
    restarts = [250000, 500000, 750000]
    restart_weights = [1, 1, 1]

    # scheduler = MultiStepLR_Restart(optimizer, lr_steps, restarts, restart_weights, gamma=0.5,
                                    # clear_state=False)

    ##############################
    # Cosine Annealing Restart
    ##############################
    ## two
    T_period = [500000, 500000]
    restarts = [500000]
    restart_weights = [1]

    ## four
    T_period = [250000, 250000, 250000, 250000]
    restarts = [250000, 500000, 750000]
    restart_weights = [1, 1, 1]

    scheduler = CosineAnnealingLR_Restart(optimizer, T_period, eta_min=1e-7, restarts=restarts,
                                          weights=restart_weights)
    optimizer._learning_rate = scheduler
    ##############################
    # Draw figure
    ##############################
    N_iter = 1000000
    lr_l = list(range(N_iter))
    for i in range(N_iter):
        scheduler.step()
        current_lr = optimizer.get_lr()
        lr_l[i] = current_lr

    import matplotlib as mpl
    from matplotlib import pyplot as plt
    import matplotlib.ticker as mtick
    mpl.style.use('default')
    import seaborn
    seaborn.set(style='whitegrid')
    seaborn.set_context('paper')

    plt.figure(1)
    plt.subplot(111)
    plt.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))
    plt.title('Title', fontsize=16, color='k')
    plt.plot(list(range(N_iter)), lr_l, linewidth=1.5, label='learning rate scheme')
    legend = plt.legend(loc='upper right', shadow=False)
    ax = plt.gca()
    labels = ax.get_xticks().tolist()
    for k, v in enumerate(labels):
        labels[k] = str(int(v / 1000)) + 'K'
    ax.set_xticklabels(labels)
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.1e'))

    ax.set_ylabel('Learning rate')
    ax.set_xlabel('Iteration')
    fig = plt.gcf()
    plt.show()
