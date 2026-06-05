from enum import Enum

class EventType(Enum):
    NEW = 'new'
    CANCEL = 'cancel'
    MODIFY = 'modify'
    TRADE = 'trade'


class OrderBook:
    def __init__(self,):
        self.bids = {}
        self.asks = {}
        self.orders = {}


    def _make_order(self, side, price, size):
        return {'side': side, 'price': price, 'size': size}
    
    def _process_events(self, event):
        if(event['event_type'] == EventType.NEW.value):
            self.process_new_event(event)
        elif(event['event_type'] == EventType.MODIFY.value):
            self.process_modify_event(event)
        elif(event['event_type'] == EventType.CANCEL.value):
            self.process_cancel_event(event)
        elif(event['event_type'] == EventType.TRADE.value):
            self.process_trade_event(event)

    def _process_new_event(self, event):
        if(event['order_id'] in self.orders):
            raise ValueError ("duplicate order")
        else:
            self.orders[event['order_id']] = self._make_order(event['side'], event['price'], event['size'])
            if event['side'] == 'bid':
                self.bids[event['price']] = self.bids.get(event['price'], 0) + event['size']
            else:
                self.asks[event['price']] = self.asks.get(event['price'], 0) + event['size']
    
    def _process_modify_event(self, event):
        if(event['order_id'] not in self.orders):
            raise ValueError('event wasnt added')
        
        order = self.orders[event['order_id']]
        if order['side'] == 'bid':
            self.bids[order['price']] = self.bids.get(order['price'], 0) - order['size'] + event['size']
        else:
            self.asks[order['price']] = self.asks.get(order['price'], 0) - order['size'] + event['size']

        self.orders[event['order_id']]['size'] = event['size']

    def _process_cancel_event(self, event):
        if(event['order_id'] not in self.orders):
            raise ValueError('event wasnt added')
        order = self.orders.pop(event['order_id'])
        if order['side'] == 'bid':
            self.bids[order['price']] -= order['size']
            if self.bids[order['price']] == 0:
                del self.bids[order['price']]
        else:
            self.asks[order['price']] -= order['size']
            if self.asks[order['price']] == 0:
                del self.asks[order['price']]

    def _process_trade_event(self, event):
        if(event['order_id'] not in self.orders):
            raise ValueError('event wasnt added')
        order = self.orders[event['order_id']]
        if order['side'] == 'bid':
            self.bids[order['price']] -= event['size']
            if self.bids[order['price']] == 0:
                del self.bids[order['price']]
        else:
            self.asks[order['price']] -= event['size']
            if self.asks[order['price']] == 0:
                del self.asks[order['price']]
        
        self.orders[event['order_id']]['size'] = order['size'] - event['size']
        if self.orders[event['order_id']]['size'] == 0:
            del self.orders[event['order_id']]
    
    def snapshot(self, depth):
        return {
            'bids': sorted(self.bids.items(), reverse=True)[:depth],
            'asks': sorted(self.asks.items())[:depth]
        }


events = [
    {'timestamp': 1, 'order_id': 'A1', 'event_type': 'new',    'side': 'bid', 'price': 213.50, 'size': 100},
    {'timestamp': 2, 'order_id': 'A2', 'event_type': 'new',    'side': 'bid', 'price': 213.45, 'size': 200},
    {'timestamp': 3, 'order_id': 'B1', 'event_type': 'new',    'side': 'ask', 'price': 213.55, 'size': 150},
    {'timestamp': 4, 'order_id': 'A1', 'event_type': 'cancel'},
    {'timestamp': 5, 'order_id': 'A2', 'event_type': 'modify',  'size': 50},
]


book = OrderBook()
for event in events:
    book._process_events(event)

print(book.snapshot(depth=5))


