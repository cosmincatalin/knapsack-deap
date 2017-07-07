import argparse
import logging

import knapsack_pb2
import pika
from solver import Solver

DESCRIPTION = """
Solves Knapsack problems that are provided via a message queue.
"""

logging.basicConfig()
logger = logging.getLogger()
hdlr = logging.FileHandler("engine.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)


def callback(ch, method, properties, body):
    del properties
    try:
        problem = knapsack_pb2.Problem()
        problem.ParseFromString(body)

        logger.info("Got a new problem to solve: {0}".format(problem.problemId))

        items = {}
        for i in range(len(problem.items)):
            items[i] = (problem.items[i].volume, problem.items[i].value, problem.items[i].name)

        solver = Solver(items, problem.knapsackVolume)
        chosen_items = solver.solve()

        logger.info("Choosing items:")
        for idx in chosen_items:
            logger.info("\t{0}".format(items[idx]))

        logger.info("Problem {0} solved. Solution saved. Acknowledging to the queue.".format(problem.problemId))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except:
        logger.info("Problem {0} cannot be solved. Will mark it as non solvable.".format(problem.problemId))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    finally:
        logger.info("All done. Waiting for the next problem.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('host', type=str, help="The host where RabbitMQ is exposed.")
    parser.add_argument('--queue', type=str, default="knapsack", help="The queue in RabbitMQ to get messages from.")

    args = parser.parse_args()

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.host))
    channel = connection.channel()
    channel.queue_declare(queue=args.queue, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(callback, queue=args.queue)
    logger.info("Knapsack Engine is ready and willing.")
    channel.start_consuming()
