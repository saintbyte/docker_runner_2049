import sys
import logging
import time
from argparse import ArgumentParser
from argparse import Namespace

import boto3
import docker
from docker import DockerClient
from docker.models.containers import Container

from logger import logger

LOG_BUFFER_SIZE: int = 10


def get_command_line_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('--docker-image', type=str, help='Name of the Docker image')
    parser.add_argument('--bash-command', type=str, help='Bash command to run inside the Docker image')
    parser.add_argument('--aws-cloudwatch-group', type=str, help='Name of the AWS CloudWatch group')
    parser.add_argument('--aws-cloudwatch-stream', type=str, help='Name of the AWS CloudWatch stream')
    parser.add_argument('--aws-access-key-id', type=str, help='AWS access key ID')
    parser.add_argument('--aws-secret-access-key', type=str, help='AWS secret access key')
    parser.add_argument('--aws-region', type=str, help='Name of the AWS region')
    return parser


def run_docker_container(client: DockerClient, args: ArgumentParser) -> Container:
    return client.containers.run(
        args.docker_image,
        command=args.bash_command,
        detach=True
    )


def get_aws_logs_client(args):
    return boto3.client(
        'logs',
        aws_access_key_id=args.aws_access_key_id,
        aws_secret_access_key=args.aws_secret_access_key,
        region_name=args.aws_region,
    )


def send_logs(aws_client, buffer: list, group_name: str, stream_name: str, sequence_token: str | None):
    logger.debug("send_logs")
    if len(buffer) == 0:
        return
    response = aws_client.put_log_events(
        logGroupName=group_name,
        logStreamName=stream_name,
        logEvents=buffer,
        sequenceToken='string'
    )
    sequence_token = response['nextSequenceToken']
    clear_log_buffer(buffer)


def clear_log_buffer(buffer: list):
    logger.debug("clear_log_buffer")
    buffer.clear()


def put_to_buffer(record, buffer):
    line: str = record.decode("utf-8").strip()
    buffer.append({
        "timestamp": int(round(time.time() * 1000)),
        "message": line,
    })


def main():
    parser: ArgumentParser = get_command_line_parser()
    args: Namespace = parser.parse_args()
    logger.debug(f"args.aws_access_key_id: {args.aws_access_key_id}")
    logger.debug(f"args.aws_secret_access_key:{args.aws_secret_access_key}" )
    logger.debug(f"args.aws_region:{args.aws_region}")
    aws_cloudwatch_client = get_aws_logs_client(args)
    log_buffer: list = []
    count: int = 0
    sequence_token: str | None = None
    try:
        aws_cloudwatch_client.create_log_group(logGroupName=args.aws_cloudwatch_group)
    except aws_cloudwatch_client.exceptions.ResourceAlreadyExistsException:
        logger.warning(f"Group {args.aws_cloudwatch_group} -- resource already exists")
    try:
        aws_cloudwatch_client.create_log_stream(
            logGroupName=args.aws_cloudwatch_group,
            logStreamName=args.aws_cloudwatch_stream
        )
    except aws_cloudwatch_client.exceptions.ResourceAlreadyExistsException:
        logger.warning(f"Stream {args.aws_cloudwatch_stream} -- resource already exists")

    docker_client: DockerClient = docker.from_env()
    container: Container = run_docker_container(docker_client, args)
    try:
        for log_record in container.logs(stream=True):
            count = count + 1
            logger.info(f"{count} {log_record}")
            put_to_buffer(log_record, log_buffer)
            if len(log_buffer) >= LOG_BUFFER_SIZE:
                send_logs(
                    aws_cloudwatch_client,
                    log_buffer,
                    args.aws_cloudwatch_group,
                    args.aws_cloudwatch_stream,
                    sequence_token,
                )
    except KeyboardInterrupt:
        logger.error("Receive Keyboard Interrupt")
    finally:
        container.stop()
        send_logs(
            aws_cloudwatch_client,
            log_buffer,
            args.aws_cloudwatch_group,
            args.aws_cloudwatch_stream,
            sequence_token,
        )


if __name__ == '__main__':
    main()
