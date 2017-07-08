import argparse
import logging
import mysql.connector

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


class RequestHandler:
    def __init__(self, conn):
        self.conn = conn

    def callback(self, ch, method, properties, body):
        del properties
        problem = knapsack_pb2.Problem()
        problem.ParseFromString(body)
        try:
            logger.info("Got a new problem to solve: {0}".format(problem.problemId))

            items = {}
            for i in range(len(problem.items)):
                items[i] = (problem.items[i].volume, problem.items[i].value, problem.items[i].name)

            solver = Solver(items, problem.knapsackVolume)
            chosen_items = solver.solve()

            items_list = []
            for idx in chosen_items:
                items_list.append('{"name":"' + str(items[idx][2]) + '","value":' + str(items[idx][1]) + ',"volume":' + str(items[idx][0]) + '}')

            solution = '{"items":[' + ",".join(items_list) + ']}'

            if not self.conn.is_connected():
                self.conn.reconnect()
            cursor = self.conn.cursor()
            query = """UPDATE problems SET solved = NOW(), solution = %s WHERE id = %s"""
            cursor.execute(query, (solution, problem.problemId))
            self.conn.commit()
            cursor.close()

            logger.info("Problem {0} solved. Solution saved. Acknowledging to the queue.".format(problem.problemId))
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logger.warning("Problem {0} cannot be solved. Will mark it as non solvable.".format(problem.problemId))
            logger.error(e)
            if not self.conn.is_connected():
                self.conn.reconnect()
            cursor = self.conn.cursor()
            query = """UPDATE problems SET wontsolve = NOW(), solution = %s WHERE id = %s"""
            cursor.execute(query, (None, problem.problemId))
            self.conn.commit()
            cursor.close()
            ch.basic_ack(delivery_tag=method.delivery_tag)
        finally:
            logger.info("All done. Waiting for the next problem.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("host", type=str, help="The host where RabbitMQ is exposed.")
    parser.add_argument("dbhost", type=str, help="The host where MySQL is exposed.")
    parser.add_argument("--queue", type=str, default="knapsack", help="The queue in RabbitMQ to get messages from.")
    parser.add_argument("--dbport", type=int, default=3306, help="MySQL port.")
    parser.add_argument("--dbuser", type=str, default="root", help="MySQL user.")
    parser.add_argument("--dbpass", type=str, default="", help="MySQL password.")
    parser.add_argument("--dbname", type=str, default="knapsack", help="MySQL database.")

    args = parser.parse_args()

    cnx = mysql.connector.connect(user=args.dbuser, password=args.dbpass,
                                  host=args.dbhost,
                                  database=args.dbname, port=args.dbport)

    reqHandler = RequestHandler(cnx)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=args.host))
    channel = connection.channel()
    channel.queue_declare(queue=args.queue, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(reqHandler.callback, queue=args.queue)
    logger.info("Knapsack Engine is ready and willing.")
    channel.start_consuming()
