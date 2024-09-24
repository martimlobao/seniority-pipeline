import asyncio
import logging
import time

import grpc

import seniority_pb2
import seniority_pb2_grpc
from config import GRPC_HOST, GRPC_PORT

logging.basicConfig(level=logging.INFO)


class SeniorityModelServicer(seniority_pb2_grpc.SeniorityModelServicer):
    def InferSeniority(  # noqa: N802
        self,
        request: seniority_pb2.SeniorityRequestBatch,
        context: grpc.aio.ServicerContext,  # noqa: ARG002
    ) -> seniority_pb2.SeniorityResponseBatch:
        responses: list[int] = []
        time.sleep(1)  # simulate max throughput of 1 batch request per second
        for seniority_request in request.batch:
            seniority_level: int = self.mock_seniority_level(
                seniority_request.company, seniority_request.title
            )
            seniority_response = seniority_pb2.SeniorityResponse(
                uuid=seniority_request.uuid, seniority=seniority_level
            )
            responses.append(seniority_response)
        return seniority_pb2.SeniorityResponseBatch(batch=responses)

    @staticmethod
    def mock_seniority_level(company: str, title: str) -> int:  # noqa: PLR0911
        # mocking the seniority level model for fun
        if "opc" in company.lower():
            return 7
        if "intern" in title.lower():
            return 1
        if "junior" in title.lower():
            return 2
        if "senior" in title.lower():
            return 3
        if "lead" in title.lower():
            return 4
        if "partner" in title.lower():
            return 6
        return 5  # otherwise, everyone is the VP of something


async def serve() -> None:
    """Starts the gRPC server to listen for requests asynchronously."""
    server = grpc.aio.server()
    seniority_pb2_grpc.add_SeniorityModelServicer_to_server(SeniorityModelServicer(), server)

    server.add_insecure_port(f"[::]:{GRPC_PORT}")
    await server.start()
    print(f"Mock gRPC server is running on {GRPC_HOST}:{GRPC_PORT}")

    # Keep the server running
    await server.wait_for_termination()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
