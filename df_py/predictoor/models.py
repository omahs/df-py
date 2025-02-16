from typing import Dict, List

from enforce_typing import enforce_types


class Prediction:
    @enforce_types
    def __init__(self, slot: int, payout: float, stake: float, contract_addr: str):
        self.slot = slot
        self.payout = payout
        self.stake = stake
        self.contract_addr = contract_addr

    @property
    def is_correct(self) -> bool:
        """
        Returns true if the prediction is correct, false otherwise.
        """
        # We assume that the prediction is wrong if the payout is 0.
        # Only predictions where the true value for their slot is submitted
        # are being counted, so this is a safe assumption.
        return self.payout > 0

    @property
    def revenue(self) -> float:
        return self.payout - self.stake

    @classmethod
    def from_query_result(cls, prediction_dict: Dict) -> "Prediction":
        """
        @description
            Creates a Prediction object from a dictionary returned by a subgraph query.
        @params
            prediction_dict: A dictionary containing the prediction data.
        @return
            A Prediction object.
        @raises
            ValueError: If the input dictionary is invalid.
        """
        try:
            contract_addr = prediction_dict["slot"]["predictContract"]["id"]
            slot = int(prediction_dict["slot"]["slot"])
            if (
                prediction_dict["payout"] is not None
                and "payout" in prediction_dict["payout"]
            ):
                payout = float(prediction_dict["payout"]["payout"])
            else:
                payout = 0.0
            stake = float(prediction_dict["stake"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid prediction dictionary") from exc
        return cls(slot, payout, stake, contract_addr)


class PredictoorBase:
    def __init__(
        self,
        address: str,
        prediction_count: int,
        correct_prediction_count: int,
        accuracy: float,
        revenue: float,
    ):
        self._address = address
        self._prediction_count = prediction_count
        self._correct_prediction_count = correct_prediction_count
        self._accuracy = accuracy
        self._revenue = revenue

    @property
    def address(self) -> str:
        return self._address

    @property
    def prediction_count(self) -> int:
        return self._prediction_count

    @property
    def correct_prediction_count(self) -> int:
        return self._correct_prediction_count

    @property
    def accuracy(self) -> float:
        return self._accuracy

    @property
    def revenue(self) -> float:
        return self._revenue


class PredictionSummary:
    @enforce_types
    def __init__(
        self,
        prediction_count,
        correct_prediction_count,
        contract_addr,
        total_payout,
        total_revenue,
        total_stake,
    ):
        self.prediction_count = prediction_count
        self.correct_prediction_count = correct_prediction_count
        self.contract_addr = contract_addr
        self.total_payout = total_payout
        self.total_revenue = total_revenue
        self.total_stake = total_stake

    @property
    def accuracy(self) -> float:
        if self.prediction_count == 0:
            return 0
        return self.correct_prediction_count / self.prediction_count


class Predictoor(PredictoorBase):
    @enforce_types
    def __init__(self, address: str):
        super().__init__(address, 0, 0, 0, 0)
        self._predictions: List[Prediction] = []

    def get_prediction_summary(self, contract_addr: str) -> PredictionSummary:
        """
        Get the prediction summary for a specific contract address.

        @param contract_addr: The contract address for which to get the prediction summary.

        @return:
            PredictionSummary - The prediction summary for the specified contract address.
        """
        prediction_count = 0
        correct_prediction_count = 0
        total_stake = 0.0
        total_payout = 0.0
        total_revenue = 0.0

        for prediction in self._predictions:
            if prediction.contract_addr != contract_addr:
                continue
            prediction_count += 1
            total_revenue += prediction.revenue
            total_stake += prediction.stake
            if prediction.is_correct:
                correct_prediction_count += 1
                total_payout += prediction.payout

        return PredictionSummary(
            prediction_count,
            correct_prediction_count,
            contract_addr,
            total_payout,
            total_revenue,
            total_stake,
        )

    @property
    def prediction_summaries(self) -> Dict[str, PredictionSummary]:
        """
        Get the summaries of all predictions made by this Predictoor.

        @return
            Dict[str, PredictionSummary] - A dict of PredictionSummary objects.
        """
        prediction_summaries = {}
        for prediction in self._predictions:
            contract_addr = prediction.contract_addr
            if contract_addr in prediction_summaries:
                continue
            prediction_summaries[contract_addr] = self.get_prediction_summary(
                contract_addr
            )

        return prediction_summaries

    @property
    def accuracy(self) -> float:
        """
        Returns the accuracy of this Predictoor

        @return
            accuracy - float
        """
        if self._prediction_count == 0:
            return 0
        return self._correct_prediction_count / self._prediction_count

    @enforce_types
    def add_prediction(self, prediction: Prediction):
        self._predictions.append(prediction)
        self._prediction_count += 1
        if prediction.is_correct:
            self._correct_prediction_count += 1
        self._revenue += prediction.revenue


class PredictContract:
    def __init__(
        self,
        chainid: int,
        address: str,
        name: str,
        symbol: str,
        blocks_per_epoch: int,
        blocks_per_subscription: int,
    ):
        self.chainid = chainid
        self.address = address.lower()
        self.name = name
        self.symbol = symbol
        self.blocks_per_epoch = blocks_per_epoch
        self.blocks_per_subscription = blocks_per_subscription

    def to_dict(self) -> Dict[str, str]:
        return {
            "chainid": str(self.chainid),
            "address": self.address,
            "name": self.name,
            "symbol": self.symbol,
            "blocks_per_epoch": str(self.blocks_per_epoch),
            "blocks_per_subscription": str(self.blocks_per_subscription),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]):
        chainid = int(data["chainid"])
        address = data["address"]
        name = data["name"]
        symbol = data["symbol"]
        blocks_per_epoch = int(data["blocks_per_epoch"])
        blocks_per_subscription = int(data["blocks_per_subscription"])

        return cls(
            chainid, address, name, symbol, blocks_per_epoch, blocks_per_subscription
        )
