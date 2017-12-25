import sys
import pickle
import copy
import io
from PyQt5 import QtCore, QtWidgets, QtGui


class Item:
    __slots__ = ('login', 'itemData', 'children', 'parent', 'check_state')

    def __init__(self, *args, parent=None):
        super().__init__()
        self.login = args[0]
        self.itemData = [''] + list(args)
        self.children = []
        self.parent = parent
        self.check_state = QtCore.Qt.Unchecked

        if parent is not None:
            self.parent.addChild(self)

    def addChild(self, child):
        self.children.append(child)
        child.parent = self

    def removeChild(self, row):
        child = self.children.pop(row)

    def child(self, row):
        try:
            return self.children[row]
        except IndexError:
            return self.children[-1]

    def childCount(self):
        return len(self.children)

    def columnCount(self):
        return len(self.itemData) + 1

    def setData(self, column, data):
        if column < 0 or column > len(self.itemData) - 1:
            return False
        self.itemData[column] = data
        return True

    def data(self, column):
        if self.parent.is_root():
            return self.login if column == 0 else ''
        return self.itemData[column] if column < len(self.itemData) else ''

    def checkState(self):
        return self.check_state

    def row(self):
        if self.parent is not None:
            return self.parent.children.index(self)

    def is_root(self):
        return self.parent is None

    def __len__(self):
        return len(self.children)

    def __repr__(self):
        return "<Item: {}; Children count {}>".format(self.login, len(self.children))

    def __hash__(self):
        return hash(self.login)


class PyObjMime(QtCore.QMimeData):
    MIMETYPE = 'application/x-pyobj'

    def __init__(self, data=None):
        super().__init__()

        self.data = data
        if data is not None:
            # Try to pickle data
            try:
                pdata = pickle.dumps(data)
            except:
                return

            self.setData(self.MIMETYPE, pickle.dumps(data.__class__) + pdata)

    def itemInstance(self):
        if self.data is not None:
            return self.data
        i_o = io.StringIO(str(self.data(self.MIMETYPE)))
        try:
            pickle.load(i_o)
            return pickle.load(i_o)
        except:
            pass
        return None


class TreeModel(QtCore.QAbstractItemModel):
    header_labels = ["Column 1", "Column 2", "Column 3"]

    def __init__(self, root, parent=None):
        super().__init__(parent)
        self.root = root

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.header_labels[section]

    def itemFromIndex(self, index):
        if index.isValid():
            return index.internalPointer()
        return self.root

    def rowCount(self, index):
        item = self.itemFromIndex(index)
        return len(item)

    def columnCount(self, index):
        return len(self.header_labels)
        # item = self.itemFromIndex(index)
        # return item.columnCount()

    def flags(self, index):
        """
        Returns whether or not the current item is editable/selectable/etc.
        """
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        enabled = QtCore.Qt.NoItemFlags
        selectable = QtCore.Qt.NoItemFlags
        editable = QtCore.Qt.NoItemFlags
        draggable = QtCore.Qt.NoItemFlags
        droppable = QtCore.Qt.NoItemFlags
        checkable = QtCore.Qt.ItemIsUserCheckable

        item = index.internalPointer()

        if not item.is_root() and not item.parent.is_root():
            draggable = QtCore.Qt.ItemIsDragEnabled
            selectable = QtCore.Qt.ItemIsSelectable
            enabled = QtCore.Qt.ItemIsEnabled

        if item.parent.is_root():
            droppable = QtCore.Qt.ItemIsDropEnabled
            enabled = QtCore.Qt.ItemIsEnabled
        if index.column() == 8:
            editable = QtCore.Qt.ItemIsEditable

        # return our flags.
        return enabled | selectable | editable | draggable | droppable | checkable

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction | QtCore.Qt.CopyAction

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            item = self.itemFromIndex(index)
            return item.data(index.column())
        if role == QtCore.Qt.CheckStateRole and index.column() == 0:
            return self.itemFromIndex(index).checkState()

    def index(self, row, column, parent):
        item = self.itemFromIndex(parent)
        if row < len(item):
            return self.createIndex(row, column, item.child(row))
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        item = self.itemFromIndex(index)
        parent = item.parent
        if parent == self.root:
            return QtCore.QModelIndex()
        return self.createIndex(parent.row(), 0, parent)

    def removeRows(self, row, count, parentIndex):
        self.beginRemoveRows(parentIndex, row, row + count - 1)
        parent = self.itemFromIndex(parentIndex)

        if not parent.is_root():
            for i in range(count):
                parent.removeChild(row)
        self.endRemoveRows()
        return True

    def mimeTypes(self):
        return ['application/x-pyobj']

    def mimeData(self, index):
        items = set(self.itemFromIndex(item) for item in index)
        mimedata = PyObjMime(items)
        return mimedata

    def dropMimeData(self, mimedata, action, row, column, parentIndex):
        item = mimedata.itemInstance()
        dropParent = self.itemFromIndex(parentIndex)
        itemCopy = copy.deepcopy(item)
        for child in itemCopy:
            dropParent.addChild(child)
        self.dataChanged.emit(parentIndex, parentIndex)
        return True

    def setCheckState(self):
        pass


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    root = Item('root')
    itemA = Item('No group', parent=root)
    itemB = Item('Group B', parent=root)
    itemC = Item('Group C', parent=root)
    itemD = Item('ItemD', 'Description D', parent=itemA)
    itemE = Item('ItemE', 'Description E', parent=itemB)
    itemF = Item('ItemF', 'Description F', parent=itemC)
    itemG = Item('ItemG', 'Description G', parent=itemC)
    itemH = Item('ItemH', 'Description H', parent=itemC)

    model = TreeModel(root)

    tree = QtWidgets.QTreeView()
    tree.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
    tree.setModel(model)
    tree.setFocusPolicy(QtCore.Qt.NoFocus)

    tree.setDragEnabled(True)
    tree.setAcceptDrops(True)
    tree.setDropIndicatorShown(True)
    tree.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
    tree.show()
    itemI = Item('ItemI', 'Description I', parent=itemC)
    tree.expandAll()
    sys.exit(app.exec_())
