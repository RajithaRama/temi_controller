import ethical_governor.blackboard.scheduler.scheduler as scheduler
# import scheduler


class RoundRobin(scheduler.Scheduler):
    def __init__(self, conf):
        self.order = conf["test_order"]

    def next(self, data):
        for item in self.order:
            yield item


if __name__ == "__main__":
    conf = {"order": [1, 2, 3, 4]}

    scheduler = RoundRobin(conf)
    for i in scheduler.next():
        print(i)

    print(scheduler.next)
