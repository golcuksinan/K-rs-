import {
    Routes,
    Route,
    Navigate
} from "react-router-dom";


import MainLayout from "../layouts/MainLayout";

import AuthLayout from "../layouts/AuthLayout";

import ProtectedRoute from "../components/ProtectedRoute";

import AdminRoute from "../components/AdminRoute";


import Home from "../pages/Home";


import Login from "../pages/Auth/Login";
import Register from "../pages/Auth/Register";
import VerifyOtp from "../pages/Auth/VerifyOtp";
import ForgotPassword from "../pages/Auth/ForgotPassword";
import ResetPassword from "../pages/Auth/ResetPassword";


import Professors from "../pages/Professors/Professors";
import ProfessorDetail from "../pages/Professors/ProfessorDetail";
import CourseProfessorDetail from "../pages/Professors/CourseProfessorDetail";


import Courses from "../pages/Courses/Courses";
import CourseDetail from "../pages/Courses/CourseDetail";


import Departments from "../pages/Departments";
import Faculties from "../pages/Faculties";
import Universities from "../pages/Universities";


import CreateReview from "../pages/Reviews/CreateReview";
import MyReviews from "../pages/Reviews/MyReviews";


import Moderation from "../pages/Admin/Moderation";
import Reports from "../pages/Admin/Reports";
import Stats from "../pages/Admin/Stats";


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

path="/hocalar/:professorId/dersler/:courseProfessorId"

element={<CourseProfessorDetail/>}

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

path="/fakulteler/:facultyId/bolumler"

element={<Departments/>}

/>



<Route

path="/universiteler/:universityId/fakulteler"

element={<Faculties/>}

/>



{/* Fakülte listesi üniversite olmadan çalışmıyor (GET /faculties university_id ister). */}
<Route

path="/fakulteler"

element={<Navigate to="/universiteler" replace/>}

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

path="/yorumlarim"

element={

<ProtectedRoute>

<MyReviews/>

</ProtectedRoute>

}

/>



<Route

path="/admin/moderasyon"

element={

<AdminRoute>

<Moderation/>

</AdminRoute>

}

/>



<Route

path="/admin/raporlar"

element={

<AdminRoute>

<Reports/>

</AdminRoute>

}

/>



<Route

path="/admin/istatistikler"

element={

<AdminRoute>

<Stats/>

</AdminRoute>

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



<Route

path="*"

element={<NotFound/>}

/>


</Route>




<Route

element={<AuthLayout/>}

>


<Route

path="/giris"

element={<Login/>}

/>



<Route

path="/kayit"

element={<Register/>}

/>



<Route

path="/kayit/dogrula"

element={<VerifyOtp/>}

/>



<Route

path="/sifremi-unuttum"

element={<ForgotPassword/>}

/>



<Route

path="/sifre-sifirla"

element={<ResetPassword/>}

/>


</Route>



</Routes>

);

}