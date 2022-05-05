import * as TYPES from "./types";
import API from "../utils/api";
import * as API_ROUTES from "../utils/apiConstants";
import Cookies from "js-cookie";
import { uid } from "../utils/helper";

export const makeLoginRequest = (details, navigate) => async (dispatch, getState) => {
  try {
    dispatch({ type: TYPES.LOADING });
    //empty the alerts
    dispatch({
      type: TYPES.USER_NOTION_ALERTS,
      payload: [],
    });
    const response = await API.post(API_ROUTES.LOGIN, {
      ...details,
    });
    if (response.status === 200 && Object.keys(response.data).length > 0) {
      let keepUser = getState().userAuth.keepLoggedIn;
      let expiryTime = keepUser ? 7 : 0.5;
      Cookies.set("isLoggedIn", true, { expires: expiryTime, secure:true });
      Cookies.set("token", response.data?.auth_token, { expires: expiryTime, secure:true });
      Cookies.set("username", response.data?.username, { expires: expiryTime, secure:true });
      navigate("/");
    }
    dispatch({ type: TYPES.COMPLETED });
  } catch (error) {
    let alerts = getState().userAuth.alerts;
    let alert = {};
    if (error?.response) {
      alert = {
        title: error?.response?.data?.message,
        key: uid(),
      };
      dispatch(toggleLoginBtn(true));
    } else {
      alert = {
        title: error?.message,
        key: uid(),
      };
      dispatch({ type: TYPES.NETWORK_ERROR });
    }
    alerts.push(alert);
    dispatch({
      type: TYPES.USER_NOTION_ALERTS,
      payload: alerts,
    });
    dispatch({ type: TYPES.COMPLETED });
  }
};

export const movePage = (toPage, navigate) => async (dispatch) => {
  //empty the alerts
  dispatch({
    type: TYPES.USER_NOTION_ALERTS,
    payload: [],
  });
  navigate(toPage);
};

export const setUserLoggedInState = (value) => async (dispatch) => {
  dispatch({
    type: TYPES.KEEP_USER_LOGGED_IN,
    payload: value,
  });
};

export const registerUser = (details, navigate) => async (dispatch, getState) => {
  try {
    dispatch({ type: TYPES.LOADING });
    //empty the alerts
    dispatch({
      type: TYPES.USER_NOTION_ALERTS,
      payload: [],
    });

    const response = await API.post(API_ROUTES.REGISTER, {
      ...details,
    });
    if (response.status === 200 ) {
      navigate("/login");
    }
    dispatch({ type: TYPES.COMPLETED });
  } catch (error) {
    let alerts = getState().userAuth.alerts;
    let alert = {};
    document.querySelector(".signup-card").scrollTo(0,0);
    if (error?.response) {
      alert = {
        title: error?.response?.data?.message,
        key: uid(),
      };
      dispatch(toggleSignupBtn(true));
    } else {
      alert = {
        title: error?.message,
        key: uid(),
      };
      dispatch({ type: TYPES.NETWORK_ERROR });
    }
    alerts.push(alert);
    dispatch({
      type: TYPES.USER_NOTION_ALERTS,
      payload: alerts,
    });
    dispatch({ type: TYPES.COMPLETED });
  }
};

export const toggleSignupBtn = ( isDisbaled ) => async( dispatch ) => {
  dispatch({
    type: TYPES.SET_SIGNUP_BUTTON,
    payload: isDisbaled,
  });
}

export const toggleLoginBtn = ( isDisbaled ) => async( dispatch ) => {
  dispatch({
    type: TYPES.SET_LOGIN_BUTTON,
    payload: isDisbaled,
  });
}