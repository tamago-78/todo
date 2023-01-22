import localforage from 'localforage';
import { useEffect, useState } from 'react';

import GlobalStyles from '@mui/material/GlobalStyles';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { indigo, pink } from '@mui/material/colors';

import { QR } from './QR';
import { ToolBar } from './ToolBar';
import { SideBar } from './SideBar';
import { TodoItem } from './TodoItem';
import { FormDialog } from './FormDialog';
import { AlertDialog } from './AlertDialog';
import { ActionButton } from './ActionButton';

import { isTodos } from './lib/isTodos';

const theme = createTheme({
  palette: {
    primary: {
      main: indigo[500],
      light: '#757de8',
      dark: '#002984',
    },
    secondary: {
      main: pink[500],
      light: '#ff6090',
      dark: '#b0003a',
    },
  },
});

export const App = () => {
  const [text, setText] = useState('');
  const [todos, setTodos] = useState<Todo[]>([]);
  const [filter, setFilter] = useState<Filter>('all');

  const [qrOpen, setQrOpen] = useState(false);
  const [alertOpen, setAlertOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);

  const onToggleQR = () => setQrOpen(!qrOpen);
  const onToggleAlert = () => setAlertOpen(!alertOpen);
  const onToggleDrawer = () => setDrawerOpen(!drawerOpen);

  const onToggleDialog = () => {
    setDialogOpen(!dialogOpen);
    setText('');
  };

  const handleOnSort = (filter: Filter) => {
    setFilter(filter);
  };

  const handleOnChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setText(e.target.value);
  };

  const handleOnSubmit = () => {
    if (!text) {
      setDialogOpen(false);
      return;
    }

    const newTodo: Todo = {
      value: text,
      id: new Date().getTime(),
      checked: false,
      removed: false,
    };

    setTodos([newTodo, ...todos]);
    setText('');
    setDialogOpen(false);
  };

  const handleOnTodo = <T extends Todo, U extends keyof Todo, V extends T[U]>(
    obj: T,
    key: U,
    value: V
  ) => {
    const deepCopy = todos.map((todo) => ({ ...todo }));

    const newTodos = deepCopy.map((todo) => {
      if (todo.id === obj.id) {
        todo[key] = value;
      }
      return todo;
    });

    setTodos(newTodos);
  };

  const handleOnEmpty = () => {
    const newTodos = todos.filter((todo) => !todo.removed);
    setTodos(newTodos);
  };

  useEffect(() => {
    localforage
      .getItem('todo-20200101')
      .then((values) => isTodos(values) && setTodos(values));
  }, []);

  useEffect(() => {
    localforage.setItem('todo-20200101', todos);
  }, [todos]);

  return (
    <ThemeProvider theme={theme}>
      <GlobalStyles styles={{ body: { margin: 0, padding: 0 } }} />
      <ToolBar filter={filter} onToggleDrawer={onToggleDrawer} />
      <SideBar
        drawerOpen={drawerOpen}
        onSort={handleOnSort}
        onToggleQR={onToggleQR}
        onToggleDrawer={onToggleDrawer}
      />
      <QR open={qrOpen} onClose={onToggleQR} />
      <FormDialog
        text={text}
        dialogOpen={dialogOpen}
        onChange={handleOnChange}
        onSubmit={handleOnSubmit}
        onToggleDialog={onToggleDialog}
      />
      <AlertDialog
        alertOpen={alertOpen}
        onToggleAlert={onToggleAlert}
        onEmpty={handleOnEmpty}
      />
      <TodoItem todos={todos} filter={filter} onTodo={handleOnTodo} />
      <ActionButton
        todos={todos}
        filter={filter}
        alertOpen={alertOpen}
        dialogOpen={dialogOpen}
        onToggleAlert={onToggleAlert}
        onToggleDialog={onToggleDialog}
      />
    </ThemeProvider>
  );
};
