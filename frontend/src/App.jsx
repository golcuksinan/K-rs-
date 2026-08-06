import {
BrowserRouter
} from "react-router-dom";


import AppRoutes from "./router/Routes";


export default function App(){


return (

<BrowserRouter>

<AppRoutes/>

</BrowserRouter>

);


}