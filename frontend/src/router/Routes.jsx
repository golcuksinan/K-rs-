import {
    Routes,
    Route
} from "react-router-dom";


import MainLayout from "../layouts/MainLayout";

import ProtectedRoute from "../components/ProtectedRoute";


import Home from "../pages/Home";


import Login from "../pages/Auth/Login";
import Register from "../pages/Auth/Register";


import Professors from "../pages/Professors/Professors";
import ProfessorDetail from "../pages/Professors/ProfessorDetail";


import Courses from "../pages/Courses/Courses";
import CourseDetail from "../pages/Courses/CourseDetail";


import Departments from "../pages/Departments";
import Faculties from "../pages/Faculties";
import Universities from "../pages/Universities";


import CreateReview from "../pages/Reviews/CreateReview";


import Profile from "../pages/Profile";


import NotFound from "../pages/NotFound";



export default function AppRoutes(){


return (

<Routes>


<Route

element={<MainLayout/>}

>


<Route

path="/"

element={<Home/>}

/>



<Route

path="/hocalar"

element={<Professors/>}

/>



<Route

path="/hocalar/:id"

element={<ProfessorDetail/>}

/>



<Route

path="/dersler"

element={<Courses/>}

/>



<Route

path="/dersler/:id"

element={<CourseDetail/>}

/>



<Route

path="/bolumler"

element={<Departments/>}

/>



<Route

path="/fakulteler"

element={<Faculties/>}

/>



<Route

path="/universiteler"

element={<Universities/>}

/>



<Route

path="/yorum-yap"

element={

<ProtectedRoute>

<CreateReview/>

</ProtectedRoute>

}

/>



<Route

path="/profil"

element={

<ProtectedRoute>

<Profile/>

</ProtectedRoute>

}

/>


</Route>




<Route

path="/giris"

element={<Login/>}

/>



<Route

path="/kayit"

element={<Register/>}

/>



<Route

path="*"

element={<NotFound/>}

/>



</Routes>

);

}